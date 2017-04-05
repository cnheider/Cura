# Copyright (c) 2017 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from UM.Job import Job
from UM.Scene.SceneNode import SceneNode
from UM.Math.Vector import Vector
from UM.Operations.SetTransformOperation import SetTransformOperation
from UM.Message import Message

from cura.ZOffsetDecorator import ZOffsetDecorator
from cura.Arrange import Arrange
from cura.ShapeArray import ShapeArray

from typing import List


class ArrangeObjectsJob(Job):
    def __init__(self, nodes: List[SceneNode], fixed_nodes: List[SceneNode], min_offset = 8):
        super().__init__()
        self._nodes = nodes
        self._fixed_nodes = fixed_nodes
        self._min_offset = min_offset

    def run(self):
        arranger = Arrange.create(fixed_nodes = self._fixed_nodes)

        # Collect nodes to be placed
        nodes_arr = []  # fill with (size, node, offset_shape_arr, hull_shape_arr)
        for node in self._nodes:
            offset_shape_arr, hull_shape_arr = ShapeArray.fromNode(node, min_offset = self._min_offset)
            nodes_arr.append((offset_shape_arr.arr.shape[0] * offset_shape_arr.arr.shape[1], node, offset_shape_arr, hull_shape_arr))

        # Sort the nodes with the biggest area first.
        nodes_arr.sort(key=lambda item: item[0])
        nodes_arr.reverse()

        # Place nodes one at a time
        start_priority = 0
        last_priority = start_priority
        last_size = None
        for size, node, offset_shape_arr, hull_shape_arr in nodes_arr:
            # For performance reasons, we assume that when a location does not fit,
            # it will also not fit for the next object (while what can be untrue).
            # We also skip possibilities by slicing through the possibilities (step = 10)
            if last_size == size:  # This optimization works if many of the objects have the same size
                start_priority = last_priority
            else:
                start_priority = 0
            best_spot = arranger.bestSpot(offset_shape_arr, start_prio=start_priority, step=10)
            x, y = best_spot.x, best_spot.y
            last_size = size
            last_priority = best_spot.priority
            if x is not None:  # We could find a place
                arranger.place(x, y, hull_shape_arr)  # take place before the next one

                node.removeDecorator(ZOffsetDecorator)
                if node.getBoundingBox():
                    center_y = node.getWorldPosition().y - node.getBoundingBox().bottom
                else:
                    center_y = 0

                transformation_operation = SetTransformOperation(node, Vector(x, center_y, y))
                transformation_operation.push()