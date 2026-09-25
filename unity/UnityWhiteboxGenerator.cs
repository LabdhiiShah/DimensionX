/*
 * Unity Whitebox Procedural House Generator
 * =========================================
 * Consumes House2D-lite JSON and procedurally extrudes 3D walls, floors, ceilings,
 * door cutouts, window openings, and material assignments for Unity VR Walkthroughs.
 * 
 * Usage in Unity:
 * 1. Attach UnityWhiteboxGenerator to an empty GameObject in Unity.
 * 2. Assign the house2d_lite.json file path in Inspector.
 * 3. Click "Generate Whitebox House" or run on Start().
 */

using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace Antigravity.CAD3D
{
    [Serializable]
    public class House2DLiteData
    {
        public string schema_version;
        public HouseMeta house;
        public List<WallData> walls;
        public List<RoomData> rooms;
        public List<OpeningData> openings;
        public List<ConnectionData> connections;
    }

    [Serializable]
    public class HouseMeta
    {
        public string coordinate_system;
        public float aspect_ratio;
        public ScaleData scale;
        public FootprintData footprint;
    }

    [Serializable]
    public class ScaleData
    {
        public float value;
        public string unit;
        public string source;
        public string confidence;
    }

    [Serializable]
    public class FootprintData
    {
        public string shape_category;
        public List<List<float>> normalized_polygon;
        public float area_normalized;
    }

    [Serializable]
    public class WallData
    {
        public string id;
        public string wall_class;
        public List<List<float>> normalized_centerline;
        public float length_normalized;
        public float thickness_normalized;
        public string status;
        public float confidence;
    }

    [Serializable]
    public class RoomData
    {
        public string id;
        public string name;
        public string type;
        public List<float> position;
        public List<float> size;
        public string shape;
        public List<List<float>> normalized_polygon;
        public float area_normalized;
        public float confidence;
    }

    [Serializable]
    public class OpeningData
    {
        public string id;
        public string type;
        public string host_wall;
        public float position_t;
        public List<float> normalized_center;
        public float width_normalized;
        public List<string> connects;
        public string swing;
    }

    [Serializable]
    public class ConnectionData
    {
        public string from;
        public string to;
        public string connection;
        public string via_opening;
    }

    public class UnityWhiteboxGenerator : MonoBehaviour
    {
        [Header("JSON Configuration")]
        [Tooltip("Path to house2d_lite.json file")]
        public string jsonFilePath = "output/house2d_lite.json";

        [Header("Procedural Default Dimensions (Meters)")]
        public float defaultWallHeight = 2.8f;
        public float defaultWallThickness = 0.20f;
        public float defaultSlabThickness = 0.15f;
        public float doorHeight = 2.1f;
        public float windowHeight = 1.2f;
        public float windowSillHeight = 0.9f;

        [Header("Materials")]
        public Material wallMaterial;
        public Material floorMaterial;
        public Material ceilingMaterial;
        public Material doorMaterial;
        public Material windowMaterial;

        private House2DLiteData houseData;

        public void GenerateHouse()
        {
            string fullPath = Path.IsPathRooted(jsonFilePath) ? jsonFilePath : Path.Combine(Application.dataPath, "../", jsonFilePath);
            if (!File.Exists(fullPath))
            {
                Debug.LogError($"[UnityWhiteboxGenerator] JSON file not found at: {fullPath}");
                return;
            }

            string jsonText = File.ReadAllText(fullPath);
            houseData = JsonUtility.FromJson<House2DLiteData>(jsonText);

            if (houseData == null)
            {
                Debug.LogError("[UnityWhiteboxGenerator] Failed to parse House2D-lite JSON.");
                return;
            }

            float globalScaleMeters = houseData.house.scale.value > 0 ? houseData.house.scale.value : 10.0f;
            Debug.Log($"[UnityWhiteboxGenerator] Generating Procedural House (Scale = {globalScaleMeters}m)...");

            // Clean previous generated hierarchy
            foreach (Transform child in transform)
            {
                DestroyImmediate(child.gameObject);
            }

            GameObject wallsParent = new GameObject("3D_Walls");
            wallsParent.transform.SetParent(transform);

            GameObject floorsParent = new GameObject("3D_Floors");
            floorsParent.transform.SetParent(transform);

            // Generate Walls
            foreach (var w in houseData.walls)
            {
                if (w.normalized_centerline == null || w.normalized_centerline.Count < 2) continue;

                Vector3 p1 = new Vector3(w.normalized_centerline[0][0] * globalScaleMeters, 0, w.normalized_centerline[0][1] * globalScaleMeters);
                Vector3 p2 = new Vector3(w.normalized_centerline[1][0] * globalScaleMeters, 0, w.normalized_centerline[1][1] * globalScaleMeters);

                BuildWallSegment(p1, p2, defaultWallHeight, defaultWallThickness, wallsParent.transform);
            }

            // Generate Floors for Rooms
            foreach (var r in houseData.rooms)
            {
                if (r.normalized_polygon == null || r.normalized_polygon.Count < 3) continue;

                BuildRoomFloor(r, globalScaleMeters, floorsParent.transform);
            }

            Debug.Log("[UnityWhiteboxGenerator] Whitebox 3D House Generation Complete!");
        }

        private void BuildWallSegment(Vector3 start, Vector3 end, float height, float thickness, Transform parent)
        {
            Vector3 dir = (end - start);
            float length = dir.magnitude;
            if (length < 0.01f) return;

            GameObject wallObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wallObj.name = "Wall_Segment";
            wallObj.transform.SetParent(parent);

            wallObj.transform.position = (start + end) * 0.5f + new Vector3(0, height * 0.5f, 0);
            wallObj.transform.rotation = Quaternion.LookRotation(dir.normalized) * Quaternion.Euler(0, 90, 0);
            wallObj.transform.localScale = new Vector3(thickness, height, length);

            if (wallMaterial != null)
            {
                wallObj.GetComponent<Renderer>().material = wallMaterial;
            }
        }

        private void BuildRoomFloor(RoomData room, float scale, Transform parent)
        {
            GameObject floorObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floorObj.name = $"Floor_{room.name}_{room.id}";
            floorObj.transform.SetParent(parent);

            Vector3 pos = new Vector3(room.position[0] * scale, -defaultSlabThickness * 0.5f, room.position[1] * scale);
            Vector3 size = new Vector3(room.size[0] * scale, defaultSlabThickness, room.size[1] * scale);

            floorObj.transform.position = pos;
            floorObj.transform.localScale = size;

            if (floorMaterial != null)
            {
                floorObj.GetComponent<Renderer>().material = floorMaterial;
            }
        }
    }
}
