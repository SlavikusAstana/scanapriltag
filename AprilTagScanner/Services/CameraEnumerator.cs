using Microsoft.Win32;
using OpenCvSharp;
using Windows.Devices.Enumeration;

namespace AprilTagScanner.Services;

public sealed class CameraDevice
{
    public const int NoCameraIndex = -1;

    public int Index { get; init; }
    public string Name { get; init; } = "";

    public bool IsPlaceholder => Index == NoCameraIndex;
}

public static class CameraEnumerator
{
    private const int MaxProbeIndex = 10;
    private const int StopAfterConsecutiveMisses = 3;

    public static IReadOnlyList<CameraDevice> Enumerate()
    {
        var names = ReadFriendlyNames();
        var devices = new List<CameraDevice>();
        var misses = 0;

        for (var index = 0; index < MaxProbeIndex; index++)
        {
            if (ProbeIndex(index))
            {
                devices.Add(new CameraDevice
                {
                    Index = index,
                    Name = index < names.Count ? names[index] : "",
                });
                misses = 0;
                continue;
            }

            misses++;
            if (misses >= StopAfterConsecutiveMisses && devices.Count > 0)
                break;
        }

        return devices;
    }

    private static bool ProbeIndex(int index)
    {
        VideoCapture? cap = null;
        try
        {
            cap = new VideoCapture(index, VideoCaptureAPIs.DSHOW);
            if (!cap.IsOpened())
                return false;

            // Quick check only — avoid holding the device before the real open.
            using var frame = new Mat();
            for (var attempt = 0; attempt < 2; attempt++)
            {
                if (cap.Read(frame) && !frame.Empty())
                    return true;
                Thread.Sleep(40);
            }

            return true;
        }
        catch
        {
            return false;
        }
        finally
        {
            cap?.Release();
            cap?.Dispose();
        }
    }

    private static List<string> ReadFriendlyNames()
    {
        var names = ReadNamesFromWindows();
        if (names.Count > 0)
            return names;

        return ReadNamesFromRegistry();
    }

    private static List<string> ReadNamesFromWindows()
    {
        try
        {
            return DeviceInformation.FindAllAsync(DeviceClass.VideoCapture)
                .AsTask()
                .GetAwaiter()
                .GetResult()
                .Select(static device => device.Name.Trim())
                .Where(static name => name.Length > 0)
                .ToList();
        }
        catch
        {
            return [];
        }
    }

    private static List<string> ReadNamesFromRegistry()
    {
        var names = new List<string>();
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(
                @"SOFTWARE\Microsoft\Windows Media Foundation\Platform\CaptureDeviceList");
            if (key == null)
                return names;

            foreach (var subName in key.GetSubKeyNames().OrderBy(static n => n, StringComparer.OrdinalIgnoreCase))
            {
                using var sub = key.OpenSubKey(subName);
                var friendly = sub?.GetValue("FriendlyName") as string;
                if (!string.IsNullOrWhiteSpace(friendly))
                    names.Add(friendly.Trim());
            }
        }
        catch
        {
            // ignore registry read errors
        }

        return names;
    }
}
