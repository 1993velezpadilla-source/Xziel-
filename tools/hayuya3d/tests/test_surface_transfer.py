from __future__ import annotations

import unittest

import numpy as np

from tools.hayuya3d.surface_transfer import (
    blend_joint_weights_from_relation,
    build_surface_transfer_relation,
    interpolate_vertex_values,
)


class SurfaceTransferTests(unittest.TestCase):
    def setUp(self):
        self.vertices=np.asarray([
            [0.0,0.0,0.0],
            [1.0,0.0,0.0],
            [0.0,1.0,0.0],
        ],dtype=np.float64)
        self.faces=np.asarray([[0,1,2]],dtype=np.int64)

    def test_inside_triangle_uses_true_barycentric_coordinates(self):
        target=np.asarray([[0.25,0.25,0.0]],dtype=np.float64)
        relation=build_surface_transfer_relation(
            self.vertices,
            self.faces,
            target,
        )
        self.assertEqual(relation.fallback_vertices,0)
        self.assertTrue(np.array_equal(
            relation.triangle_vertex_ids[0],
            np.asarray([0,1,2],dtype=np.int64),
        ))
        self.assertTrue(np.allclose(
            relation.barycentric[0],
            np.asarray([0.5,0.25,0.25]),
            atol=1e-8,
        ))
        self.assertAlmostEqual(
            float(relation.surface_distance[0]),
            0.0,
            places=8,
        )

    def test_joint_weights_follow_triangle_barycentrics(self):
        target=np.asarray([[1.0/3.0,1.0/3.0,0.0]],dtype=np.float64)
        relation=build_surface_transfer_relation(
            self.vertices,
            self.faces,
            target,
        )
        joints=np.asarray([
            [0,0,0,0],
            [1,0,0,0],
            [2,0,0,0],
        ],dtype=np.int64)
        weights=np.asarray([
            [1.0,0.0,0.0,0.0],
            [1.0,0.0,0.0,0.0],
            [1.0,0.0,0.0,0.0],
        ],dtype=np.float64)
        out_joints,out_weights=blend_joint_weights_from_relation(
            joints,
            weights,
            relation,
        )
        active={
            int(joint):float(weight)
            for joint,weight in zip(out_joints[0],out_weights[0])
            if float(weight)>1e-7
        }
        self.assertEqual(set(active),{0,1,2})
        self.assertAlmostEqual(active[0],1.0/3.0,places=6)
        self.assertAlmostEqual(active[1],1.0/3.0,places=6)
        self.assertAlmostEqual(active[2],1.0/3.0,places=6)
        self.assertAlmostEqual(float(np.sum(out_weights[0])),1.0,places=7)

    def test_morph_delta_uses_same_surface_relation(self):
        target=np.asarray([[0.25,0.25,0.0]],dtype=np.float64)
        relation=build_surface_transfer_relation(
            self.vertices,
            self.faces,
            target,
        )
        deltas=np.asarray([
            [0.0,0.0,0.0],
            [0.0,0.0,1.0],
            [0.0,0.0,2.0],
        ],dtype=np.float64)
        out=interpolate_vertex_values(deltas,relation)
        self.assertEqual(out.shape,(1,3))
        self.assertTrue(np.allclose(
            out[0],
            np.asarray([0.0,0.0,0.75]),
            atol=1e-8,
        ))

    def test_outside_triangle_clamps_to_nearest_edge(self):
        target=np.asarray([[0.75,0.75,0.0]],dtype=np.float64)
        relation=build_surface_transfer_relation(
            self.vertices,
            self.faces,
            target,
        )
        bary=relation.barycentric[0]
        self.assertTrue(np.all(bary>=-1e-10))
        self.assertAlmostEqual(float(np.sum(bary)),1.0,places=8)
        self.assertAlmostEqual(float(bary[0]),0.0,places=7)
        self.assertAlmostEqual(float(bary[1]),0.5,places=7)
        self.assertAlmostEqual(float(bary[2]),0.5,places=7)
        self.assertAlmostEqual(
            float(relation.surface_distance[0]),
            np.sqrt(0.125),
            places=7,
        )

    def test_progressive_search_finds_large_triangle_with_far_centroid(self):
        vertices=[
            [-100.0,-100.0,0.0],
            [100.0,-100.0,0.0],
            [0.0,100.0,0.0],
        ]
        faces=[[0,1,2]]

        # Forty tiny distractor triangles have centroids and vertices much
        # closer to the target than the giant triangle's centroid/vertices,
        # but their surfaces sit above z=0. The exact search must expand past
        # the initial KD shortlist and recover the giant zero-distance face.
        for index in range(40):
            angle=2.0*np.pi*float(index)/40.0
            cx=0.25*np.cos(angle)
            cy=0.25*np.sin(angle)
            base=len(vertices)
            vertices.extend([
                [cx-0.01,cy-0.01,0.05],
                [cx+0.01,cy-0.01,0.05],
                [cx,cy+0.01,0.05],
            ])
            faces.append([base,base+1,base+2])

        relation=build_surface_transfer_relation(
            np.asarray(vertices,dtype=np.float64),
            np.asarray(faces,dtype=np.int64),
            np.asarray([[0.0,0.0,0.0]],dtype=np.float64),
            candidate_triangles=4,
        )
        self.assertEqual(relation.fallback_vertices,0)
        self.assertAlmostEqual(
            float(relation.surface_distance[0]),
            0.0,
            places=8,
        )
        self.assertEqual(
            set(int(x) for x in relation.triangle_vertex_ids[0]),
            {0,1,2},
        )
        self.assertGreater(relation.max_examined_triangles,4)

    def test_degenerate_triangle_falls_back_to_nearest_vertex(self):
        vertices=np.asarray([
            [0.0,0.0,0.0],
            [1.0,0.0,0.0],
            [2.0,0.0,0.0],
        ],dtype=np.float64)
        target=np.asarray([[0.9,0.2,0.0]],dtype=np.float64)
        relation=build_surface_transfer_relation(
            vertices,
            self.faces,
            target,
        )
        self.assertEqual(relation.fallback_vertices,1)
        self.assertTrue(np.array_equal(
            relation.triangle_vertex_ids[0],
            np.asarray([1,1,1],dtype=np.int64),
        ))
        self.assertTrue(np.allclose(
            relation.barycentric[0],
            np.asarray([1.0,0.0,0.0]),
        ))


if __name__=="__main__":
    unittest.main()
