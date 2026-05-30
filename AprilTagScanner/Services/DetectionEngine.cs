using AprilTagScanner.Models;
using OpenCvSharp;
using OpenCvSharp.Aruco;

namespace AprilTagScanner.Services;

public sealed class DetectionEngine : IDisposable
{
    private readonly object _lock = new();
    private readonly Thread _worker;
    private volatile bool _running = true;
    private volatile bool _busy;

    private Mat? _pendingBgr;
    private int _detectWidth;
    private IReadOnlyList<string> _families = [];
    private bool _probe;
    private float _decimate = 1.5f;

    private List<DetectedTag> _lastTags = [];
    private double _lastMs;
    private int _cacheVersion;

    private readonly Dictionary<(string Family, bool Probe), Dictionary> _dictCache = [];

    public DetectionEngine()
    {
        _worker = new Thread(WorkerLoop) { IsBackground = true, Name = "AprilTagDetect" };
        _worker.Start();
    }

    public void BumpCache() => Interlocked.Increment(ref _cacheVersion);

    public void Configure(float decimate) => _decimate = decimate;

    public bool TrySubmit(Mat bgrFrame, int detectWidth, IReadOnlyList<string> families, bool probe)
    {
        if (families.Count == 0)
            return false;

        Mat clone;
        try
        {
            clone = bgrFrame.Clone();
        }
        catch
        {
            return false;
        }

        lock (_lock)
        {
            if (_busy)
            {
                clone.Dispose();
                return false;
            }

            _pendingBgr?.Dispose();
            _pendingBgr = clone;
            _detectWidth = detectWidth;
            _families = families;
            _probe = probe;
            _busy = true;
            Monitor.Pulse(_lock);
            return true;
        }
    }

    public (IReadOnlyList<DetectedTag> Tags, double Ms, bool Busy) Snapshot()
    {
        lock (_lock)
        {
            return (_lastTags.ToList(), _lastMs, _busy);
        }
    }

    private static Mat PrepareGray(Mat bgr, int detectWidth, out float invScale)
    {
        var w = bgr.Width;
        var h = bgr.Height;
        var scale = Math.Min(1.0, detectWidth / (double)w);
        if (scale < 1.0)
        {
            var small = new Mat();
            Cv2.Resize(
                bgr,
                small,
                new Size((int)(w * scale), (int)(h * scale)),
                interpolation: InterpolationFlags.Area
            );
            var gray = new Mat();
            Cv2.CvtColor(small, gray, ColorConversionCodes.BGR2GRAY);
            small.Dispose();
            invScale = (float)(1.0 / scale);
            return gray;
        }

        invScale = 1f;
        var direct = new Mat();
        Cv2.CvtColor(bgr, direct, ColorConversionCodes.BGR2GRAY);
        return direct;
    }

    private Dictionary GetDictionary(string family, bool probe)
    {
        var key = (family, probe);
        if (_dictCache.TryGetValue(key, out var dict))
            return dict;

        dict = CvAruco.GetPredefinedDictionary(TagFamilyCatalog.ToDictionary(family));
        _dictCache[key] = dict;
        return dict;
    }

    private void WorkerLoop()
    {
        var localCacheVersion = -1;
        var parameters = new DetectorParameters();

        while (_running)
        {
            Mat? bgr = null;
            int detectWidth;
            IReadOnlyList<string> families;
            bool probe;

            lock (_lock)
            {
                while (_running && _pendingBgr == null)
                    Monitor.Wait(_lock, 50);

                if (!_running)
                    break;

                bgr = _pendingBgr;
                _pendingBgr = null;
                detectWidth = _detectWidth;
                families = _families;
                probe = _probe;
            }

            if (bgr == null)
                continue;

            Mat? gray = null;
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var found = new List<DetectedTag>();

            try
            {
                gray = PrepareGray(bgr, detectWidth, out var invScale);

                if (localCacheVersion != _cacheVersion)
                {
                    foreach (var d in _dictCache.Values)
                        d.Dispose();
                    _dictCache.Clear();
                    localCacheVersion = _cacheVersion;
                }

                foreach (var family in families)
                {
                    var dict = GetDictionary(family, probe);
                    CvAruco.DetectMarkers(gray, dict, out var corners, out var ids, parameters, out _);
                    if (ids == null || corners == null || ids.Length == 0)
                        continue;

                    for (var i = 0; i < ids.Length; i++)
                    {
                        var scaled = corners[i]
                            .Select(p => new Point2f(p.X * invScale, p.Y * invScale))
                            .ToArray();
                        found.Add(new DetectedTag
                        {
                            Family = family,
                            Id = ids[i],
                            Corners = scaled,
                        });
                    }
                }
            }
            catch
            {
                found.Clear();
            }
            finally
            {
                gray?.Dispose();
                bgr.Dispose();
            }

            sw.Stop();
            lock (_lock)
            {
                _lastTags = found;
                _lastMs = sw.Elapsed.TotalMilliseconds;
                _busy = false;
            }
        }
    }

    public void Dispose()
    {
        _running = false;
        lock (_lock)
        {
            _pendingBgr?.Dispose();
            _pendingBgr = null;
            Monitor.Pulse(_lock);
        }

        if (_worker.IsAlive)
            _worker.Join(TimeSpan.FromSeconds(1));

        foreach (var d in _dictCache.Values)
            d.Dispose();
        _dictCache.Clear();
    }
}
