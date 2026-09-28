using System;
using System.Linq;
using UnityEngine;
using UnityEditor;

/// <summary>
/// Editor-only tool for bootstrapping a scene: pick a furniture type and a
/// style from the catalog, click Place, and it drops a correctly-tagged
/// FurnitureSlot instance into the scene at the given position — so it's
/// immediately swappable by FurnitureSyncManager once you enter Play Mode.
///
/// Setup:
/// 1. Copy this file into an "Editor" folder anywhere under Assets
///    (e.g. Assets/Editor/FurnitureCatalogWindow.cs) — it must be in a
///    folder literally named "Editor" or Unity will fail to build.
/// 2. Copy furniture_data.json into Assets/Resources/furniture_data.json
///    (Unity Resources.Load needs it there, without the .json extension
///    in the load call).
/// 3. Open it from the menu: DimensionsX > Furniture Placement Tool.
/// </summary>
public class FurnitureCatalogWindow : EditorWindow
{
    [Serializable] private class TypeRow { public int type_id; public string type_name; }
    [Serializable] private class StyleRow { public int style_id; public int type_id; public string style_name; public string prefab_path; }
    [Serializable] private class Catalog { public TypeRow[] types; public StyleRow[] styles; }

    private Catalog _catalog;
    private Vector2 _scroll;
    private Vector3 _placementPosition = Vector3.zero;
    private Vector3 _placementRotationEuler = Vector3.zero;
    private Transform _parent;
    private string _loadError;

    [MenuItem("DimensionsX/Furniture Placement Tool")]
    public static void Open()
    {
        var window = GetWindow<FurnitureCatalogWindow>("Furniture Placement");
        window.LoadCatalog();
    }

    private void LoadCatalog()
    {
        _loadError = null;
        var text = Resources.Load<TextAsset>("furniture_data");
        if (text == null)
        {
            _loadError = "Couldn't find Assets/Resources/furniture_data.json. Copy it there and reopen this window.";
            return;
        }
        try
        {
            _catalog = JsonUtility.FromJson<Catalog>(text.text);
        }
        catch (Exception e)
        {
            _loadError = "Failed to parse furniture_data.json: " + e.Message;
        }
    }

    private void OnGUI()
    {
        EditorGUILayout.Space(6);
        if (GUILayout.Button("Reload catalog")) LoadCatalog();

        if (!string.IsNullOrEmpty(_loadError))
        {
            EditorGUILayout.HelpBox(_loadError, MessageType.Error);
            return;
        }
        if (_catalog == null) { EditorGUILayout.HelpBox("Loading...", MessageType.Info); return; }

        EditorGUILayout.Space(4);
        EditorGUILayout.LabelField("Placement settings", EditorStyles.boldLabel);
        _placementPosition = EditorGUILayout.Vector3Field("Position", _placementPosition);
        _placementRotationEuler = EditorGUILayout.Vector3Field("Rotation (euler)", _placementRotationEuler);
        _parent = (Transform)EditorGUILayout.ObjectField("Parent (optional)", _parent, typeof(Transform), true);
        EditorGUILayout.HelpBox("Tip: select an object in the Scene/Hierarchy first, then click 'Use selected transform' to grab its position + rotation (e.g. a placeholder cube you roughed the layout out with).", MessageType.None);
        if (GUILayout.Button("Use selected transform's position + rotation") && Selection.activeTransform != null)
        {
            _placementPosition = Selection.activeTransform.position;
            _placementRotationEuler = Selection.activeTransform.rotation.eulerAngles;
        }

        EditorGUILayout.Space(10);
        EditorGUILayout.LabelField("Catalog", EditorStyles.boldLabel);
        _scroll = EditorGUILayout.BeginScrollView(_scroll);

        foreach (var type in _catalog.types)
        {
            var styles = _catalog.styles.Where(s => s.type_id == type.type_id).ToArray();
            EditorGUILayout.Space(4);
            EditorGUILayout.LabelField($"{type.type_name}  (type_id {type.type_id})", EditorStyles.boldLabel);

            if (styles.Length == 0)
            {
                EditorGUILayout.LabelField("  No styles in catalog yet.");
                continue;
            }

            foreach (var style in styles)
            {
                EditorGUILayout.BeginHorizontal();
                EditorGUILayout.LabelField($"  {style.style_name}", GUILayout.Width(160));
                EditorGUILayout.LabelField(style.prefab_path, EditorStyles.miniLabel);
                if (GUILayout.Button("Place", GUILayout.Width(60)))
                    PlaceStyle(type, style);
                EditorGUILayout.EndHorizontal();
            }
        }

        EditorGUILayout.EndScrollView();
    }

    private void PlaceStyle(TypeRow type, StyleRow style)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(style.prefab_path);
        if (prefab == null)
        {
            Debug.LogError($"[FurnitureCatalogWindow] Prefab not found at {style.prefab_path}");
            return;
        }

        var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab, _parent);
        instance.transform.position = _placementPosition;
        instance.transform.rotation = Quaternion.Euler(_placementRotationEuler);
        instance.name = $"{type.type_name} ({style.style_name})";

        var slot = instance.GetComponent<FurnitureSlot>();
        if (slot == null) slot = instance.AddComponent<FurnitureSlot>();
        slot.typeId = type.type_id;
        slot.styleId = style.style_id;
        slot.label = style.style_name;

        Selection.activeGameObject = instance;
        Undo.RegisterCreatedObjectUndo(instance, "Place Furniture");

        Debug.Log($"[FurnitureCatalogWindow] Placed {type.type_name} / {style.style_name} at {_placementPosition}");
    }
}