"""Wrapper that adds Gaussian noise to the actions."""

from typing import Optional, Union

import dm_env
import numpy as np
import tree
from dm_env import specs

from dm_env_wrappers._src import base


class ActionNoiseWrapper(base.EnvironmentWrapper):
    """Wrapper that adds Gaussian noise to the actions.

    The scale argument specifies the standard deviation of the Gaussian noise as a
    fraction of the max-min range of each action dimension. This only affects action
    specs of type `specs.BoundedArray`.
    """

    def __init__(
        self,
        environment: dm_env.Environment,
        scale: float = 0.01,
        random_state: Optional[Union[np.random.RandomState, int]] = None,
    ) -> None:
        super().__init__(environment)

        if scale < 0:
            raise ValueError("scale must be non-negative.")

        self._action_spec = environment.action_spec()
        self._scale = scale

        if random_state is None:
            # If dm_control.suite task, try env.task.random.
            # If dm_control.composer environment, try env.random_state.
            # If neither, create a new random state.
            if not hasattr(environment, "task"):
                self._random_state = np.random.RandomState()
            else:
                try:
                    self._random_state = environment.task.random
                except AttributeError:
                    try:
                        self._random_state = environment.random_state
                    except AttributeError:
                        self._random_state = np.random.RandomState()
        else:
            if isinstance(random_state, int):
                self._random_state = np.random.RandomState(random_state)
            else:
                self._random_state = random_state
        assert isinstance(self._random_state, np.random.RandomState)

    def step(self, action) -> dm_env.TimeStep:
        if self._scale > 0:
            action = _corrupt_nested_action(
                action, self._action_spec, self._scale, self._random_state
            )
        return self._environment.step(action)


def _corrupt_nested_action(
    nested_action, nested_spec, scale: float, random_state: np.random.RandomState
):
    """Adds Gaussian noise to a nested action."""

    def _corrupt_action(action: np.ndarray, spec: specs.Array):
        if isinstance(spec, specs.BoundedArray):
            noise_stddev = scale * (spec.maximum - spec.minimum)
            action += random_state.normal(scale=noise_stddev)
            np.clip(action, spec.minimum, spec.maximum, out=action)
        return action

    return tree.map_structure(_corrupt_action, nested_action, nested_spec)
