#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Renders a picture of every furniture prefab under Assets/Furniture and saves
/// them as PNGs, so the website's furniture cards can show the real thing.
///
/// HOW TO USE
///   1. Put this file in  Assets/Editor/  (create the folder if it doesn't exist).
///   2. Menu:  DimensionsX  >  Export Furniture Thumbnails
///   3. Pick the website's  public/furniture  folder as the destination.
///   4. Refresh the website - cards now show the real pictures.
///
/// FILE NAMES  (must match the website - see prefabSlug() in src/data/catalog.js)
///   Assets/Furniture/Sofa/Couch_Large1.prefab  ->  sofa_couch_large1.png
///   <parent folder>_<prefab name>, lower-cased. The folder is included because
///   "sc.prefab" exists in both chair/ and Desk/.
///
/// If a picture faces the wrong way, change CameraDirection below (try (-1, 0.6, -1)).
/// </summary>
public static class FurnitureThumbnailExporter
{
    const string FurnitureRoot = "Assets/Furniture";
    const int Size = 512;
    static readonly Vector3 CameraDirection = new Vector3(1f, 0.6f, 1f);   // where the camera sits, relative to the piece
    static readonly Color Background = new Color(0.965f, 0.945f, 0.914f, 1f); // same soft cream as the website cards

    [MenuItem("DimensionsX/Export Furniture Thumbnails")]
    public static void Export()
    {
        string outDir = EditorUtility.SaveFolderPanel(
            "Save thumbnails to... (pick your website's public/furniture folder)", "", "furniture");
        if (string.IsNullOrEmpty(outDir)) return;

        string[] guids = AssetDatabase.FindAssets("t:Prefab", new[] { FurnitureRoot });
        if (guids.Length == 0)
        {
            EditorUtility.DisplayDialog("No prefabs found", "Nothing found under " + FurnitureRoot + ".", "OK");
            return;
        }

        int done = 0, skipped = 0;
        try
        {
            for (int i = 0; i < guids.Length; i++)
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guids[i]);
                EditorUtility.DisplayProgressBar("Exporting furniture thumbnails", assetPath, (float)i / guids.Length);

                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
                byte[] png = prefab != null ? RenderPrefab(prefab) : null;
                if (png == null) { skipped++; Debug.LogWarning("[Thumbnails] Skipped (no renderers?): " + assetPath); continue; }

                File.WriteAllBytes(Path.Combine(outDir, SlugFor(assetPath) + ".png"), png);
                done++;
            }
        }
        finally { EditorUtility.ClearProgressBar(); }

        Debug.Log("[Thumbnails] Wrote " + done + " thumbnail(s) to " + outDir + (skipped > 0 ? " (" + skipped + " skipped)" : ""));
        EditorUtility.RevealInFinder(outDir);
    }

    // Must stay identical to prefabSlug() in the website's src/data/catalog.js
    static string SlugFor(string assetPath)
    {
        string file = Path.GetFileNameWithoutExtension(assetPath);
        string folder = Path.GetFileName(Path.GetDirectoryName(assetPath) ?? "");
        return (folder + "_" + file).ToLowerInvariant();
    }

    static byte[] RenderPrefab(GameObject prefab)
    {
        var preview = new PreviewRenderUtility();
        GameObject instance = null;
        try
        {
            instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            instance.transform.position = Vector3.zero;

            var renderers = instance.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0) return null;
            Bounds b = renderers[0].bounds;
            for (int i = 1; i < renderers.Length; i++) b.Encapsulate(renderers[i].bounds);

            preview.AddSingleGO(instance);

            preview.cameraFieldOfView = 30f;
            preview.camera.clearFlags = CameraClearFlags.SolidColor;
            preview.camera.backgroundColor = Background;
            preview.ambientColor = new Color(0.4f, 0.4f, 0.4f, 1f);
            preview.lights[0].intensity = 1.1f;
            preview.lights[0].transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            preview.lights[1].intensity = 0.6f;
            preview.lights[1].transform.rotation = Quaternion.Euler(340f, 218f, 177f);

            // Back the camera off just far enough that the whole piece fits.
            float radius = Mathf.Max(b.extents.magnitude, 0.01f);
            float distance = radius / Mathf.Sin(preview.cameraFieldOfView * 0.5f * Mathf.Deg2Rad) * 1.05f;
            preview.camera.nearClipPlane = 0.01f;
            preview.camera.farClipPlane = distance * 4f + 100f;
            preview.camera.transform.position = b.center + CameraDirection.normalized * distance;
            preview.camera.transform.LookAt(b.center);

            preview.BeginStaticPreview(new Rect(0, 0, Size, Size));
            preview.Render(true); // true = use the project's render pipeline (URP) so materials aren't pink
            Texture2D tex = preview.EndStaticPreview();

            byte[] png = tex.EncodeToPNG();
            Object.DestroyImmediate(tex);
            return png;
        }
        finally
        {
            if (instance != null) Object.DestroyImmediate(instance);
            preview.Cleanup();
        }
    }
}
#endif
