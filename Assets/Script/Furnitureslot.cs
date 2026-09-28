using UnityEngine;

/// <summary>
/// Attach this to every placed furniture instance in the scene (the bed,
/// the sofa, the sink, etc.). It tags the object with the catalog
/// type_id and style_id it currently represents so FurnitureSyncManager
/// can find "the sofa slot" and swap what's in it without you having to
/// wire up references by hand.
///
/// On Awake it registers itself with FurnitureSyncManager. When the
/// manager swaps this slot for a new prefab, it copies this component's
/// values onto the new instance and re-registers it.
/// </summary>
[DisallowMultipleComponent]
public class FurnitureSlot : MonoBehaviour
{
    [Tooltip("Must match a type_id from the `type` table (e.g. 1 = Bed, 7 = Sink).")]
    public int typeId;

    [Tooltip("The style_id currently occupying this slot (from the `style` table). Kept in sync automatically after a swap.")]
    public int styleId;

    [Tooltip("Optional human-readable label, shown in logs/inspector only.")]
    public string label;

    [Tooltip("Set automatically for furniture placed via drag-and-drop (place_furniture). Left blank for the original catalog-swap slots.")]
    public string instanceId;

    [Tooltip("Set automatically wherever this object was spawned from. Used to reload it after restarting Play mode.")]
    public string prefabPath;

    [Tooltip("This instance's own scale at the moment it was placed/swapped in — its natural/authored size. Resizing is applied as a multiplier of THIS, not as an absolute number, so pieces imported at wildly different native scales still resize sensibly. Set automatically — don't edit by hand.")]
    public Vector3 baseScale = Vector3.one;

    [Tooltip("Current size relative to baseScale. 1 = original size, 1.5 = 150%, 0.5 = 50%. Kept within FurnitureSyncManager's minInstanceScale/maxInstanceScale. Set automatically — don't edit by hand.")]
    public float scaleMultiplier = 1f;

    void Awake()
    {
        if (FurnitureSyncManager.Instance != null)
            FurnitureSyncManager.Instance.RegisterSlot(typeId, gameObject);
    }

    void OnDestroy()
    {
        if (FurnitureSyncManager.Instance != null)
            FurnitureSyncManager.Instance.UnregisterSlot(typeId, gameObject);
    }
}