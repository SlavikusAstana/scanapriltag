using AprilTagScanner.Models;

namespace AprilTagScanner.Services;

public sealed class ScanSession
{
    private readonly object _lock = new();
    private readonly HashSet<TagKey> _visibleNow = [];
    private readonly Dictionary<TagKey, int> _missCounts = [];
    private readonly List<TagRecord> _records = [];
    private readonly HashSet<TagKey> _duplicates = [];

    public IReadOnlyList<TagRecord> Records
    {
        get { lock (_lock) return _records.ToList(); }
    }

    public IReadOnlySet<TagKey> Duplicates
    {
        get { lock (_lock) return _duplicates.ToHashSet(); }
    }

    public void Reset()
    {
        lock (_lock)
        {
            _records.Clear();
            _duplicates.Clear();
            _visibleNow.Clear();
            _missCounts.Clear();
        }
    }

    public void ClearTracking()
    {
        lock (_lock)
        {
            _visibleNow.Clear();
            _missCounts.Clear();
        }
    }

    public bool ShouldRecord(TagKey key, out bool isDuplicate)
    {
        lock (_lock)
            return ShouldRecordUnlocked(key, out isDuplicate);
    }

    private bool ShouldRecordUnlocked(TagKey key, out bool isDuplicate)
    {
        isDuplicate = false;
        var lastPos = -1;
        for (var i = 0; i < _records.Count; i++)
        {
            if (new TagKey(_records[i].Family, _records[i].Id) == key)
                lastPos = i;
        }

        if (lastPos < 0)
            return true;

        for (var i = lastPos + 1; i < _records.Count; i++)
        {
            if (new TagKey(_records[i].Family, _records[i].Id) != key)
            {
                isDuplicate = true;
                return true;
            }
        }

        return false;
    }

    public TagRecord? TryAppend(DetectedTag tag)
    {
        lock (_lock)
            return TryAppendUnlocked(tag);
    }

    private TagRecord? TryAppendUnlocked(DetectedTag tag)
    {
        if (!ShouldRecordUnlocked(tag.Key, out var isDup))
            return null;

        var record = new TagRecord
        {
            Family = tag.Family,
            Id = tag.Id,
            Duplicate = isDup,
        };
        if (isDup)
            _duplicates.Add(tag.Key);
        _records.Add(record);
        return record;
    }

    public IReadOnlyList<TagRecord> ProcessDetections(IReadOnlyList<DetectedTag> tags, int missLimit)
    {
        lock (_lock)
        {
            var detected = new Dictionary<TagKey, DetectedTag>();
            foreach (var tag in tags)
                detected.TryAdd(tag.Key, tag);

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
                var record = TryAppendUnlocked(detected[key]);
                if (record != null)
                    appended.Add(record);
                _visibleNow.Add(key);
                _missCounts[key] = 0;
            }

            return appended;
        }
    }
}
