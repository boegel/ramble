# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import string
import ast
import six
import operator

import ramble.error

supported_math_operators = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow:
    operator.pow, ast.BitXor: operator.xor, ast.USub: operator.neg
}


class ExpansionDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


class Expander(object):
    """A class that will track and expand keyword arguments

    This class will track variables and their definitions, to allow for
    expansion within string.

    The variables can come from workspace variables, software stack variables,
    and experiment variables.

    Additionally, math will be evaluated as part of expansion.
    """

    def __init__(self, variables):
        self._variables = variables

        self._application_name = None
        self._workload_name = None
        self._experiment_name = None

        self._application_namespace = None
        self._workload_namespace = None
        self._experiment_namespace = None
        self._spec_namespace = None

        self._application_input_dir = None
        self._workload_input_dir = None

        self._application_run_dir = None
        self._workload_run_dir = None
        self._experiment_run_dir = None

    @property
    def application_name(self):
        if not self._application_name:
            self._application_name = self.expand_var('{application_name}')

        return self._application_name

    @property
    def workload_name(self):
        if not self._workload_name:
            self._workload_name = self.expand_var('{workload_name}')

        return self._workload_name

    @property
    def experiment_name(self):
        if not self._experiment_name:
            self._experiment_name = self.expand_var('{experiment_name}')

        return self._experiment_name

    @property
    def application_namespace(self):
        if not self._application_namespace:
            self._application_namespace = self.application_name

        return self._application_namespace

    @property
    def workload_namespace(self):
        if not self._workload_namespace:
            self._workload_namespace = '%s.%s' % (self.application_name,
                                                  self.workload_name)

        return self._workload_namespace

    @property
    def experiment_namespace(self):
        if not self._experiment_namespace:
            self._experiment_namespace = '%s.%s.%s' % (self.application_name,
                                                       self.workload_name,
                                                       self.experiment_name)

        return self._experiment_namespace

    @property
    def spec_namespace(self):
        if not self._spec_namespace:
            self._spec_namespace = self.expand_var('{spec_name}.{workload_name}')

        return self._spec_namespace

    @property
    def application_input_dir(self):
        if not self._application_input_dir:
            self._application_input_dir = self.expand_var('{application_input_dir}')

        return self._application_input_dir

    @property
    def workload_input_dir(self):
        if not self._workload_input_dir:
            self._workload_input_dir = self.expand_var('{workload_input_dir}')

        return self._workload_input_dir

    @property
    def application_run_dir(self):
        if not self._application_run_dir:
            self._application_run_dir = self.expand_var('{application_run_dir}')

        return self._application_run_dir

    @property
    def workload_run_dir(self):
        if not self._workload_run_dir:
            self._workload_run_dir = self.expand_var('{workload_run_dir}')

        return self._workload_run_dir

    @property
    def experiment_run_dir(self):
        if not self._experiment_run_dir:
            self._experiment_run_dir = self.expand_var('{experiment_run_dir}')

        return self._experiment_run_dir

    def expand_var(self, var, extra_vars=None):
        """Perform expansion of a string

        Expand a string by building up a dict of all
        expansion variables.
        """

        expansions = self._variables
        if extra_vars:
            expansions = self._variables.copy()
            expansions.update(extra_vars)

        expanded = self._partial_expand(expansions, str(var))

        if self._fully_expanded(expanded):
            try:
                math_ast = ast.parse(str(expanded), mode='eval')
                evaluated = self.eval_math(math_ast.body)
                expanded = evaluated
            except MathEvaluationError:
                pass
            except SyntaxError:
                pass

        return str(expanded).lstrip()

    def _all_keywords(self, in_str):
        if isinstance(in_str, six.string_types):
            for keyword in string.Formatter().parse(in_str):
                if keyword[1]:
                    yield keyword[1]

    def _fully_expanded(self, in_str):
        for kw in self._all_keywords(in_str):
            return False
        return True

    def eval_math(self, node):
        """Evaluate math from parsing the AST

        Does not assume a specific type of operands.
        Some operators will generate floating point, while
        others will generate integers (if the inputs are integers).
        """
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left_eval = self.eval_math(node.left)
            right_eval = self.eval_math(node.right)
            op = supported_math_operators[type(node.op)]
            return op(left_eval, right_eval)
        elif isinstance(node, ast.UnaryOp):
            operand = self.eval_math(node.operand)
            op = supported_math_operators[type(node.op)]
            return op(operand)
        else:
            raise MathEvaluationError('Invalid node')

    def _partial_expand(self, expansion_vars, in_str):
        """Perform expansion of a string with some variables

        args:
          expansion_vars (dict): Variables to perform expansion with
          in_str (str): Input template string to expand

        returns:
          in_str (str): Expanded version of input string
        """

        exp_dict = ExpansionDict()
        if isinstance(in_str, six.string_types):
            for kw in self._all_keywords(in_str):
                if kw in expansion_vars:
                    exp_dict[kw] = \
                        self._partial_expand(expansion_vars,
                                             expansion_vars[kw])

            for kw, val in exp_dict.items():
                if self._fully_expanded(val):
                    try:
                        math_ast = ast.parse(str(val), mode='eval')
                        evaluated = self.eval_math(math_ast.body)
                        exp_dict[kw] = evaluated
                    except MathEvaluationError:
                        pass
                    except SyntaxError:
                        pass

            return in_str.format_map(exp_dict)
        return in_str


class ExpanderError(ramble.error.RambleError):
    """Raised when an error happens within an expander"""


class MathEvaluationError(ExpanderError):
    """Raised when an error happens while evaluating math during
    expansion
    """


class ApplicationNotDefinedError(ExpanderError):
    """Raised when an application is not defined properly"""


class WorkloadNotDefinedError(ExpanderError):
    """Raised when a workload is not defined properly"""


class ExperimentNotDefinedError(ExpanderError):
    """Raised when an experiment is not defined properly"""
