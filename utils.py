# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; version 2
#  of the License.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import math

import bmesh
import bpy
import mathutils

from . import bounding_box, global_def


def InitBMesh():
    """ Init global bmesh. """
    global_def.bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    global_def.bm.faces.ensure_lookup_table()
    # uvlayer = bm.loops.layers.uv.active

    global_def.uvlayer = global_def.bm.loops.layers.uv.verify()
    global_def.bm.faces.layers.tex.verify()


def update():
    bmesh.update_edit_mesh(bpy.context.edit_object.data, False, False)
    # bm.to_mesh(bpy.context.object.data)
    # bm.free()


def GBBox(islands):
    minX = minY = 1000
    maxX = maxY = -1000
    for _island in islands:
        for face_id in _island.faceList:
            face = global_def.bm.faces[face_id]
            for loop in face.loops:
                u, v = loop[global_def.uvlayer].uv
                minX = min(u, minX)
                minY = min(v, minY)
                maxX = max(u, maxX)
                maxY = max(v, maxY)

    return bounding_box.BoundingBox(mathutils.Vector((minX, minY)),
                                    mathutils.Vector((maxX, maxY)))


def vectorDistance(vector1, vector2):
    return math.sqrt(
        math.pow((vector2.x - vector1.x), 2) +
        math.pow((vector2.y - vector1.y), 2))


def snapIsland(island, targetIsland, threshold):
    """ snap 'island' to 'targetIsland' """

    bestMatcherList = []
    activeUvLayer = global_def.bm.loops.layers.uv.active

    for face_id in targetIsland.faceList:
        face = global_def.bm.faces[face_id]

        for loop in face.loops:
            selectedUVvert = loop[activeUvLayer]
            uvList = []

            for active_face_id in island:
                active_face = global_def.bm.faces[active_face_id]

                for active_loop in active_face.loops:
                    activeUVvert = active_loop[activeUvLayer].uv

                    dist = vectorDistance(selectedUVvert.uv, activeUVvert)
                    uvList.append((dist, active_loop[activeUvLayer]))

            # for every vert in uvList take the ones with the shortest
            # distnace from ref

            minDist = uvList[0][0]
            bestMatcher = 0

            # 1st pass get lower dist
            for bestDist in uvList:
                if bestDist[0] <= minDist:
                    minDist = bestDist[0]

            # 2nd pass get the only ones with a match
            for bestVert in uvList:
                if bestVert[0] <= minDist:
                    bestMatcherList.append((bestVert[0], selectedUVvert,
                                            bestVert[1].uv))

    for bestMatcher in bestMatcherList:
        if bestMatcher[0] <= threshold:
            bestMatcher[1].uv = bestMatcher[2]


# todo: change param order
def snapToUnselected(island, targetIslands, threshold):
    bestMatcherList = []
    # targetIslands.faceList.remove(island.faceList)
    activeUvLayer = global_def.bm.loops.layers.uv.active

    for face_id in island.faceList:
        face = global_def.bm.faces[face_id]

        for loop in face.loops:
            selectedUVvert = loop[activeUvLayer]
            uvList = []

            for targetIsland in targetIslands.faceList:
                for targetFace_id in targetIsland:
                    targetFace = global_def.bm.faces[targetFace_id]

                    for targetLoop in targetFace.loops:
                        # take the a reference vert
                        targetUvVert = targetLoop[activeUvLayer].uv
                        # get a selected vert and calc it's distance from
                        # the ref
                        # add it to uvList
                        dist = round(vectorDistance(selectedUVvert.uv,
                                                    targetUvVert), 10)
                        uvList.append((dist, targetLoop[activeUvLayer]))

            # for every vert in uvList take the ones with the shortest
            # distnace from ref
            minDist = uvList[0][0]
            bestMatcher = 0

            # 1st pass get lower dist
            for bestDist in uvList:
                if bestDist[0] <= minDist:
                    minDist = bestDist[0]

            # 2nd pass get the only ones with a match
            for bestVert in uvList:
                if bestVert[0] <= minDist:
                    bestMatcherList.append((bestVert[0], selectedUVvert,
                                            bestVert[1].uv))
    for bestMatcher in bestMatcherList:
        if bestMatcher[0] <= threshold:
            bestMatcher[2].uv = bestMatcher[1]


def _sortCenter(pointList):

    scambio = True
    n = len(pointList)
    while scambio:
        scambio = False
        for i in range(0, n-1):
            pointA = pointList[i][0]
            pointB = pointList[i+1][0]

            if (pointA.x <= pointB.x) and (pointA.y > pointB.y):
                pointList[i], pointList[i+1] = pointList[i+1], pointList[i]
                scambio = True

    return pointList


def _sortVertex(vertexList, BBCenter):

    anglesList = []
    for v in vertexList:
        # atan2(P[i].y - M.y, P[i].x - M.x)
        angle = math.atan2(v.uv.y - BBCenter.y, v.uv.x - BBCenter.x)
        anglesList.append((v, angle))

    vertsAngle = sorted(anglesList, key=lambda coords: coords[0].uv)
    # vertsAngle = sorted(anglesList, key=lambda angle: angle[1])
    newList = []
    for i in vertsAngle:
        newList.append(i[0])

    return newList


def getTargetPoint(context, islands):
    if context.scene.relativeItems == 'UV_SPACE':
        return mathutils.Vector((0.0, 0.0)), mathutils.Vector((1.0, 1.0))
    elif context.scene.relativeItems == 'ACTIVE':
        activeIsland = islands.activeIsland()
        if not activeIsland:
            return None
        else:
            return activeIsland.BBox()
    elif context.scene.relativeItems == 'CURSOR':
        return context.space_data.cursor_location


# deprecated: 
# def IslandSpatialSortX(islands):
#     spatialSort = []
#     for _island in islands:
#         spatialSort.append((island.BBox().center().x, island))
#     spatialSort.sort()
#     return spatialSort


# def IslandSpatialSortY(islands):
#     spatialSort = []
#     for _island in islands:
#         spatialSort.append((_island.BBox().center().y, island))
#     spatialSort.sort()
#     return spatialSort


# todo: to rework
def averageIslandDist(islands):
    distX = 0
    distY = 0
    counter = 0

    for i in range(len(islands)):
        elem1 = islands[i].BBox().bottomRight()
        try:            # island
            elem2 = islands[i + 1].BBox().topLeft()
            counter += 1
        except:
            break

        distX += elem2.x - elem1.x
        distY += elem2.y - elem1.y

    avgDistX = distX / counter
    avgDistY = distY / counter
    return mathutils.Vector((avgDistX, avgDistY))
