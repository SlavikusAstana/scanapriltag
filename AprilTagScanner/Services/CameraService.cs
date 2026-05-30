using OpenCvSharp;

namespace AprilTagScanner.Services;

public enum CameraErrorKind
{
    None,
    Timeout,
    NotResponding,
}

public sealed class CameraService : IDisposable
{
    private VideoCapture? _capture;
    private readonly object _lock = new();

    public static CameraOpenResult OpenWithTimeout(int index, TimeSpan timeout)
    {
        var task = Task.Run(() => OpenWithRetries(index));
        if (!task.Wait(timeout))
            return CameraOpenResult.Fail(index, CameraErrorKind.Timeout);

        return task.Result;
    }

    private static CameraOpenResult OpenWithRetries(int index)
    {
        CameraOpenResult? last = null;
        for (var attempt = 0; attempt < 3; attempt++)
        {
            if (attempt > 0)
                Thread.Sleep(450);

            last = OpenInternal(index);
            if (last.Success)
                return last;
        }

        return last ?? CameraOpenResult.Fail(index, CameraErrorKind.NotResponding);
    }

    private static CameraOpenResult OpenInternal(int index)
    {
        var backends = new (VideoCaptureAPIs Api, string Name)[]
        {
            (VideoCaptureAPIs.DSHOW, "DirectShow"),
            (VideoCaptureAPIs.MSMF, "Media Foundation"),
            (VideoCaptureAPIs.ANY, "Auto"),
        };

        Exception? lastError = null;
        foreach (var (api, name) in backends)
        {
            VideoCapture? cap = null;
            try
            {
                cap = new VideoCapture(index, api);
                if (!cap.IsOpened())
                {
                    cap.Dispose();
                    continue;
                }

                cap.Set(VideoCaptureProperties.BufferSize, 1);

                using var probe = new Mat();
                for (var i = 0; i < 10; i++)
                    cap.Grab();

                var warmedUp = false;
                for (var i = 0; i < 20; i++)
                {
                    if (cap.Read(probe) && !probe.Empty())
                    {
                        warmedUp = true;
                        break;
                    }

                    Thread.Sleep(100);
                }

                if (!warmedUp)
                {
                    cap.Release();
                    cap.Dispose();
                    continue;
                }

                cap.Set(VideoCaptureProperties.FrameWidth, 1280);
                cap.Set(VideoCaptureProperties.FrameHeight, 720);
                return CameraOpenResult.Ok(cap, index, name);
            }
            catch (Exception ex)
            {
                lastError = ex;
                cap?.Dispose();
            }
        }

        return CameraOpenResult.Fail(index, CameraErrorKind.NotResponding, lastError?.Message ?? "");
    }

    public void Attach(VideoCapture capture)
    {
        lock (_lock)
        {
            Close();
            _capture = capture;
        }
    }

    public bool TryRead(out Mat frame)
    {
        frame = new Mat();
        lock (_lock)
        {
            if (_capture == null || !_capture.IsOpened())
                return false;

            return _capture.Read(frame) && !frame.Empty();
        }
    }

    public void Close()
    {
        lock (_lock)
        {
            _capture?.Release();
            _capture?.Dispose();
            _capture = null;
        }
    }

    public void Dispose() => Close();
}

public sealed class CameraOpenResult
{
    public bool Success { get; init; }
    public VideoCapture? Capture { get; init; }
    public int Index { get; init; }
    public string Backend { get; init; } = "";
    public CameraErrorKind ErrorKind { get; init; }
    public string Error { get; init; } = "";

    public static CameraOpenResult Ok(VideoCapture capture, int index, string backend) =>
        new() { Success = true, Capture = capture, Index = index, Backend = backend };

    public static CameraOpenResult Fail(int index, CameraErrorKind kind, string? detail = null) =>
        new() { Success = false, Index = index, ErrorKind = kind, Error = detail ?? "" };
}
