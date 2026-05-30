using AprilTagScanner.Models;

namespace AprilTagScanner.Services;

public sealed class ScanSession
{
    private readonly HashSet<TagKey> _visibleNow = [];
    private readonly Dictionary<TagKey, int> _missCounts = [];

    public List<TagRecord> Records { get; } = [];
    public HashSet<TagKey> Duplicates { get; } = [];

    public void Reset()
    {
        Records.Clear();
        Duplicates.Clear();
        _visibleNow.Clear();
        _missCounts.Clear();
    }

    public void ClearTracking()
    {
        _visibleNow.Clear();
        _missCounts.Clear();
    }

    public bool ShouldRecord(TagKey key, out bool isDuplicate)
    {
        isDuplicate = false;
        var keys = Records.Select(r => new TagKey(r.Family, r.Id)).ToList();
        if (!keys.Contains(key))
            return true;

        var lastPos = keys.FindLastIndex(k => k == key);
        var otherSince = keys.Skip(lastPos + 1).Any(k => k != key);
        if (!otherSince)
            return false;

        isDuplicate = true;
        return true;
    }

    public TagRecord? TryAppend(DetectedTag tag)
    {
        if (!ShouldRecord(tag.Key, out var isDup))
            return null;

        var record = new TagRecord
        {
            Family = tag.Family,
            Id = tag.Id,
            Duplicate = isDup,
        };
        if (isDup)
            Duplicates.Add(tag.Key);
        Records.Add(record);
        return record;
    }

    public IReadOnlyList<TagRecord> ProcessDetections(IReadOnlyList<DetectedTag> tags, int missLimit)
    {
        var detected = tags.ToDictionary(t => t.Key);
        var appended = new List<TagRecord>();

        foreach (var key in _visibleNow.ToList())
        {
            if (detected.ContainsKey(key))
            {
                _missCounts[key] = 0;
                continue;
            }

            var missed = _missCounts.GetValueOrDefault(key) + 1;
            _missCounts[key] = missed;
            if (missed >= missLimit)
            {
                _visibleNow.Remove(key);
                _missCounts.Remove(key);
            }
        }

        var newKeys = detected.Keys.Except(_visibleNow)
            .OrderBy(k => detected[k].Center.Y)
            .ThenBy(k => detected[k].Center.X)
            .ToList();

        foreach (var key in newKeys)
        {
            var record = TryAppend(detected[key]);
            if (record != null)
                appended.Add(record);
            _visibleNow.Add(key);
            _missCounts[key] = 0;
        }

        return appended;
    }
}
