
using System;
using System.IO;
using UnityEditor;
using UnityEngine;

public class FurnitureThumbnailExporter : EditorWindow
{
    private const string FurnitureFolder = "Assets/Furniture";

    private const string OutputFolder =
        @"C:\Users\saumy\Downloads\dimxfull\dimx-website\client\public\furniture";

    private string[] prefabGuids;
    private int currentIndex;
    private int waitFrames;
    private int exported;
    private int skipped;
    private bool exporting;

    [MenuItem("DimensionX/Export Furniture Thumbnails")]
    public static void OpenWindow()
    {
        GetWindow<FurnitureThumbnailExporter>(
            "Furniture Thumbnails"
        );
    }

    private void OnGUI()
    {
        EditorGUILayout.LabelField(
            "DimensionX Furniture Thumbnail Exporter",
            EditorStyles.boldLabel
        );

        EditorGUILayout.HelpBox(
            "Creates PNG thumbnails from actual Unity furniture prefabs " +
            "and saves them into the website's public/furniture folder.",
            MessageType.Info
        );

        EditorGUILayout.LabelField("Exported", exported.ToString());
        EditorGUILayout.LabelField("Skipped", skipped.ToString());

        if (exporting)
        {
            EditorGUILayout.LabelField(
                "Progress",
                $"{currentIndex} / {prefabGuids.Length}"
            );

            if (GUILayout.Button("Cancel Export"))
            {
                EditorApplication.update -= ExportNext;
                exporting = false;
            }
        }
        else if (GUILayout.Button("Export All Furniture Thumbnails"))
        {
            StartExport();
        }
    }

    private void StartExport()
    {
        if (!Directory.Exists(FurnitureFolder))
        {
            Debug.LogError(
                "[Thumbnail Export] Cannot find " + FurnitureFolder
            );
            return;
        }

        Directory.CreateDirectory(OutputFolder);

        prefabGuids = AssetDatabase.FindAssets(
            "t:Prefab",
            new[] { FurnitureFolder }
        );

        currentIndex = 0;
        waitFrames = 0;
        exported = 0;
        skipped = 0;
        exporting = true;

        EditorApplication.update -= ExportNext;
        EditorApplication.update += ExportNext;

        Debug.Log(
            $"[Thumbnail Export] Found {prefabGuids.Length} prefabs."
        );
    }

    private void ExportNext()
    {
        if (!exporting)
            return;

        if (currentIndex >= prefabGuids.Length)
        {
            FinishExport();
            return;
        }

        string assetPath = AssetDatabase.GUIDToAssetPath(
            prefabGuids[currentIndex]
        );

        GameObject prefab =
            AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);

        if (prefab == null)
        {
            SkipCurrent("Could not load prefab: " + assetPath);
            return;
        }

        // Unity generates asset previews asynchronously.
        Texture2D preview = AssetPreview.GetAssetPreview(prefab);

        if (preview == null)
        {
            waitFrames++;

            if (waitFrames < 300)
                return;

            SkipCurrent("Preview unavailable: " + assetPath);
            return;
        }

        try
        {
            string folderName =
                Path.GetFileName(Path.GetDirectoryName(assetPath));

            string prefabName =
                Path.GetFileNameWithoutExtension(assetPath);

            // Matches the website's catalog.js thumbnail naming.
            string fileName =
                (folderName + "_" + prefabName).ToLowerInvariant()
                + ".png";

            string outputPath = Path.Combine(
                OutputFolder,
                fileName
            );

            File.WriteAllBytes(outputPath, preview.EncodeToPNG());

            exported++;

            Debug.Log(
                "[Thumbnail Export] Saved: " + outputPath
            );
        }
        catch (Exception e)
        {
            Debug.LogWarning(
                "[Thumbnail Export] Failed: " + assetPath +
                "\n" + e.Message
            );

            skipped++;
        }

        currentIndex++;
        waitFrames = 0;
        Repaint();
    }

    private void SkipCurrent(string message)
    {
        Debug.LogWarning("[Thumbnail Export] " + message);
        skipped++;
        currentIndex++;
        waitFrames = 0;
        Repaint();
    }

    private void FinishExport()
    {
        EditorApplication.update -= ExportNext;
        exporting = false;

        AssetDatabase.Refresh();

        Debug.Log(
            $"[Thumbnail Export] Finished! Exported: {exported}, " +
            $"Skipped: {skipped}. Output: {OutputFolder}"
        );

        Repaint();
    }

    private void OnDisable()
    {
        EditorApplication.update -= ExportNext;
        exporting = false;
    }
}
