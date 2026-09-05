using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;

namespace Antigravity.CAD3D
{
    // =========================================================================
    // JSON DATA MODELS (MATCHES converted.json 1-TO-1 FOR Unity JsonUtility)
    // =========================================================================

    [Serializable]
    public class Vector3Data
    {
        public float x;
        public float y;
        public float z;

        public Vector3 ToVector3()
        {
            return new Vector3(x, y, z);
        }
    }

    [Serializable]
    public class TransformData
    {
        public Vector3Data position;
        public Vector3Data rotation_euler;
        public Vector3Data scale;
    }

    [Serializable]
    public class PropertyData
    {
        public float height;
        public float thickness;
    }

    [Serializable]
    public class WallData
    {
        public string id;
        public string type;
        public string detection_mode;
        public float confidence_score;
        public PropertyData properties;
        public TransformData unity_transform;
    }

    [Serializable]
    public class OpeningData
    {
        public string id;
        public string layer;
        public string type;
        public float[] position;
        public TransformData unity_transform;
    }

    [Serializable]
    public class BoundsData
    {
        public float[] min;
        public float[] max;
        public float[] center;
    }

    [Serializable]
    public class Metadata
    {
        public string dxf_file;
        public string units;
        public BoundsData bounds;
    }

    [Serializable]
    public class FloorPlanData
    {
        public Metadata metadata;
        public WallData[] walls;
        public OpeningData[] doors;
        public OpeningData[] windows;
    }

    // =========================================================================
    // UNITY 3D FLOOR PLAN RENDERER COMPONENT
    // =========================================================================

    public class FloorPlanBuilder : MonoBehaviour
    {
        [Header("JSON Configuration")]
        [Tooltip("Path to converted.json file (Absolute path or relative to project root)")]
        public string jsonFilePath = @"D:\end game\module\converted.json";

        [Header("Spawn Settings")]
        [Range(0.0f, 1.0f)]
        [Tooltip("Filter out walls below this confidence score")]
        public float minConfidenceThreshold = 0.5f;

        public bool generateWalls = true;
        public bool generateDoors = true;
        public bool generateWindows = true;
        public bool generateFloorPlane = true;

        [Header("Materials & Styling")]
        public Material wallMaterial;
        public Material doorMaterial;
        public Material windowMaterial;
        public Material floorMaterial;

        [Header("Optional Prefab Overrides (Leave empty to use Primitives)")]
        public GameObject doorPrefab;
        public GameObject windowPrefab;

        private GameObject floorPlanContainer;

        // =========================================================================
        // CONTEXT MENU / PUBLIC BUILD METHOD
        // =========================================================================

        [ContextMenu("Build 3D Floor Plan")]
        public void BuildFloorPlan()
        {
            string resolvedPath = ResolvePath(jsonFilePath);

            if (!File.Exists(resolvedPath))
            {
                Debug.LogError($"[FloorPlanBuilder] JSON file not found at: {resolvedPath}");
                return;
            }

            string jsonContent = File.ReadAllText(resolvedPath);
            FloorPlanData data = JsonUtility.FromJson<FloorPlanData>(jsonContent);

            if (data == null || data.walls == null)
            {
                Debug.LogError($"[FloorPlanBuilder] Failed to parse JSON content from: {resolvedPath}");
                return;
            }

            ClearExisting();

            floorPlanContainer = new GameObject($"3D_FloorPlan_{data.metadata.dxf_file}");
            floorPlanContainer.transform.SetParent(transform);

            // 1. Build Walls
            if (generateWalls && data.walls != null)
            {
                GameObject wallsGroup = new GameObject("Walls");
                wallsGroup.transform.SetParent(floorPlanContainer.transform);

                int wallCount = 0;
                foreach (WallData wall in data.walls)
                {
                    if (wall.confidence_score >= minConfidenceThreshold)
                    {
                        SpawnWall(wall, wallsGroup.transform);
                        wallCount++;
                    }
                }
                Debug.Log($"[FloorPlanBuilder] Successfully spawned {wallCount} 3D walls.");
            }

            // 2. Build Doors
            if (generateDoors && data.doors != null && data.doors.Length > 0)
            {
                GameObject doorsGroup = new GameObject("Doors");
                doorsGroup.transform.SetParent(floorPlanContainer.transform);

                foreach (OpeningData door in data.doors)
                {
                    SpawnOpening(door, doorsGroup.transform, doorPrefab, doorMaterial, new Color(0.8f, 0.4f, 0.1f, 1f));
                }
                Debug.Log($"[FloorPlanBuilder] Successfully spawned {data.doors.Length} doors.");
            }

            // 3. Build Windows
            if (generateWindows && data.windows != null && data.windows.Length > 0)
            {
                GameObject windowsGroup = new GameObject("Windows");
                windowsGroup.transform.SetParent(floorPlanContainer.transform);

                foreach (OpeningData window in data.windows)
                {
                    SpawnOpening(window, windowsGroup.transform, windowPrefab, windowMaterial, new Color(0.2f, 0.6f, 0.9f, 0.5f));
                }
                Debug.Log($"[FloorPlanBuilder] Successfully spawned {data.windows.Length} windows.");
            }

            // 4. Build Floor Plane
            if (generateFloorPlane && data.metadata != null && data.metadata.bounds != null)
            {
                GenerateFloorPlane(data.metadata.bounds, floorPlanContainer.transform);
            }

            Debug.Log("[FloorPlanBuilder] 3D Floor Plan Build Completed Successfully!");
        }

        [ContextMenu("Clear Floor Plan")]
        public void ClearExisting()
        {
            if (floorPlanContainer != null)
            {
                DestroyImmediate(floorPlanContainer);
            }

            Transform existing = transform.Find($"3D_FloorPlan_");
            if (existing != null)
            {
                DestroyImmediate(existing.gameObject);
            }

            // Clean up any child containers
            for (int i = transform.childCount - 1; i >= 0; i--)
            {
                DestroyImmediate(transform.GetChild(i).gameObject);
            }
        }

        // =========================================================================
        // WALL SPAWNER
        // =========================================================================

        private void SpawnWall(WallData wall, Transform parent)
        {
            GameObject wallObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wallObj.name = $"{wall.id}_{wall.detection_mode}";
            wallObj.transform.SetParent(parent);

            TransformData t = wall.unity_transform;

            wallObj.transform.position = t.position.ToVector3();
            wallObj.transform.eulerAngles = t.rotation_euler.ToVector3();
            wallObj.transform.localScale = t.scale.ToVector3();

            if (wallMaterial != null)
            {
                wallObj.GetComponent<Renderer>().material = wallMaterial;
            }
            else
            {
                // Default clean white/gray wall color
                Material defaultMat = new Material(Shader.Find("Standard"));
                defaultMat.color = new Color(0.9f, 0.9f, 0.92f);
                wallObj.GetComponent<Renderer>().material = defaultMat;
            }
        }

        // =========================================================================
        // OPENING SPAWNER (DOORS & WINDOWS)
        // =========================================================================

        private void SpawnOpening(OpeningData opening, Transform parent, GameObject prefabOverride, Material mat, Color defaultColor)
        {
            GameObject obj;
            TransformData t = opening.unity_transform;

            if (prefabOverride != null)
            {
                obj = Instantiate(prefabOverride, parent);
                obj.name = opening.id;
            }
            else
            {
                obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                obj.name = opening.id;
                obj.transform.SetParent(parent);

                if (mat != null)
                {
                    obj.GetComponent<Renderer>().material = mat;
                }
                else
                {
                    Material defaultMat = new Material(Shader.Find("Standard"));
                    defaultMat.color = defaultColor;
                    obj.GetComponent<Renderer>().material = defaultMat;
                }
            }

            obj.transform.position = t.position.ToVector3();
            obj.transform.eulerAngles = t.rotation_euler.ToVector3();
            obj.transform.localScale = t.scale.ToVector3();
        }

        // =========================================================================
        // FLOOR PLANE GENERATOR
        // =========================================================================

        private void GenerateFloorPlane(BoundsData bounds, Transform parent)
        {
            if (bounds.min == null || bounds.max == null || bounds.min.Length < 2 || bounds.max.Length < 2)
                return;

            float minX = bounds.min[0] - 2.0f;
            float maxX = bounds.max[0] + 2.0f;
            float minZ = bounds.min[1] - 2.0f;
            float maxZ = bounds.max[1] + 2.0f;

            float width = maxX - minX;
            float depth = maxZ - minZ;
            float centerX = (minX + maxX) / 2.0f;
            float centerZ = (minZ + maxZ) / 2.0f;

            GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor_Plane";
            floor.transform.SetParent(parent);

            // Position floor plane slightly below 0
            floor.transform.position = new Vector3(centerX, -0.1f, centerZ);
            floor.transform.localScale = new Vector3(width, 0.2f, depth);

            if (floorMaterial != null)
            {
                floor.GetComponent<Renderer>().material = floorMaterial;
            }
            else
            {
                Material defaultFloorMat = new Material(Shader.Find("Standard"));
                defaultFloorMat.color = new Color(0.75f, 0.75f, 0.75f);
                floor.GetComponent<Renderer>().material = defaultFloorMat;
            }
        }

        // =========================================================================
        // PATH RESOLVER
        // =========================================================================

        private string ResolvePath(string path)
        {
            if (Path.IsPathRooted(path))
            {
                return path;
            }

            return Path.Combine(Application.dataPath, path);
        }
    }
}
