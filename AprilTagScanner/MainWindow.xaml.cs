using System.Collections.ObjectModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using AprilTagScanner.Localization;
using AprilTagScanner.Models;
using AprilTagScanner.Services;
using Microsoft.Win32;
using OpenCvSharp;

namespace AprilTagScanner;

public partial class MainWindow
{
    private const int ProbeWidth = 560;
    private const int ProbeStride = 4;

    private readonly CameraService _camera = new();
    private readonly DetectionEngine _detector = new();
    private readonly ScanSession _session = new();
    private readonly DispatcherTimer _timer;
    private readonly ObservableCollection<LiveLine> _liveLines = [];

    private bool _scanning;
    private bool _familyLocked;
    private int _frameIndex;
    private int _probeFamilyIndex;
    private int _currentCameraIndex = -1;
    private bool _refreshingCameras;
    private string _selectedFamily = "tag36h11";
    private SpeedPreset _preset = SpeedPreset.Balanced;

    private string? _probeCandidateFamily;
    private int _probeCandidateId = -1;
    private int _probeCandidateStreak;

    private readonly Queue<double> _frameTimes = new(30);

    public MainWindow()
    {
        InitializeComponent();
        LiveList.ItemsSource = _liveLines;

        foreach (var family in TagFamilyCatalog.AllFamilies)
            FamilyCombo.Items.Add(family);
        FamilyCombo.SelectedItem = "tag36h11";

        InitPresetCombo();
        InitCameraCombo();

        InitLanguageSelector();

        _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(33) };
        _timer.Tick += FrameTimer_OnTick;

        Loaded += (_, _) =>
        {
            InitGeneratorTab();
            ApplyLocalization();
            RefreshCameraList(startCameraAfter: true);
        };
        Closed += (_, _) => Shutdown();
        KeyDown += MainWindow_OnKeyDown;
    }

    private sealed class LiveLine
    {
        public required string Text { get; init; }
        public bool Duplicate { get; init; }
    }

    private bool AutoProbeMode => !_scanning && !_familyLocked && MultiFamilyCheck.IsChecked != true;

    private IReadOnlyList<string> ActiveFamilies()
    {
        if (MultiFamilyCheck.IsChecked == true)
            return TagFamilyCatalog.MultiFamilies;
        return [_selectedFamily];
    }

    private string FamiliesDescription() => string.Join(", ", ActiveFamilies());

    private void StartCamera()
    {
        var index = GetSelectedCameraIndex();
        if (index < 0)
        {
            StatusText.Text = L.S("CameraNoneFound");
            StartButton.IsEnabled = false;
            ResetButton.IsEnabled = false;
            return;
        }

        StatusText.Text = L.S("CameraConnecting");

        Task.Run(() =>
        {
            try
            {
                Thread.Sleep(250);
                var result = CameraService.OpenWithTimeout(index, TimeSpan.FromSeconds(15));
                Dispatcher.BeginInvoke(() => OnCameraReady(result));
            }
            catch (Exception ex)
            {
                Dispatcher.BeginInvoke(() =>
                {
                    StatusText.Text = L.F("CameraErrorStatus", ex.Message);
                    StartButton.IsEnabled = false;
                    ResetButton.IsEnabled = false;
                });
            }
        });
    }

    private void OnCameraReady(CameraOpenResult result)
    {
        if (!result.Success || result.Capture == null)
        {
            StatusText.Text = L.F(
                "CameraOpenFailedStatus",
                result.Index,
                DescribeCameraError(result));
            StartButton.IsEnabled = false;
            ResetButton.IsEnabled = false;
            return;
        }

        _camera.Attach(result.Capture);
        _currentCameraIndex = result.Index;
        ApplyDetectorConfig();
        StatusText.Text =
            L.F("CameraReady", result.Index, result.Backend);
        StartButton.IsEnabled = true;
        ResetButton.IsEnabled = true;
        if (!_timer.IsEnabled)
            _timer.Start();
    }

    private void ApplyDetectorConfig()
    {
        var (width, decimate, _) = SpeedPresetSettings.Get(_preset);
        _detector.Configure(decimate);
        _detector.BumpCache();
        Title = AutoProbeMode
            ? L.S("TitleAutoDetect")
            : $"{L.AppTitle} - {string.Join("+", ActiveFamilies().Select(f => f.Replace("tag", "")))}";
    }

    private static string DescribeCameraError(CameraOpenResult result) =>
        result.ErrorKind switch
        {
            CameraErrorKind.Timeout => L.S("CameraTimeout"),
            CameraErrorKind.NotResponding => L.S("CameraNotResponding"),
            _ => result.Error,
        };

    private void FrameTimer_OnTick(object? sender, EventArgs e)
    {
        if (!_camera.TryRead(out var frame))
            return;

        var sw = System.Diagnostics.Stopwatch.StartNew();
        _frameIndex++;

        var (tags, detectMs, _) = _detector.Snapshot();
        RequestDetection(frame);

        if (_scanning)
        {
            var miss = ParseInt(MissBox.Text, 8);
            var added = _session.ProcessDetections(tags, miss);
            foreach (var record in added)
            {
                var suffix = record.Duplicate ? L.S("DuplicateMark") : "";
                _liveLines.Add(new LiveLine
                {
                    Text = $"{_session.Records.Count}. {record.Label}{suffix}",
                    Duplicate = record.Duplicate,
                });
                if (record.Duplicate)
                {
                    StatusText.Text = L.F("StatusDuplicate", record.Label);
                    if (BeepCheck.IsChecked == true)
                        System.Media.SystemSounds.Exclamation.Play();
                }
            }
        }
        else
        {
            _session.ClearTracking();
            TryAutoSelectFamily(tags);
        }

        DrawTags(frame, tags);
        PreviewImage.Source = MatToBitmap(frame);
        UpdateCount(tags.Count);

        sw.Stop();
        TrackFps(sw.Elapsed.TotalMilliseconds, detectMs);
        frame.Dispose();
    }

    private void RequestDetection(Mat frame)
    {
        if (AutoProbeMode)
        {
            if (_frameIndex % ProbeStride != 0)
                return;
            var family = TagFamilyCatalog.ProbePriority[_probeFamilyIndex % TagFamilyCatalog.ProbePriority.Count];
            if (_detector.TrySubmit(frame, ProbeWidth, [family], probe: true))
                _probeFamilyIndex++;
            return;
        }

        var (_, _, stride) = SpeedPresetSettings.Get(_preset);
        if (_frameIndex % stride != 0 && !_scanning)
            return;

        var (width, _, _) = SpeedPresetSettings.Get(_preset);
        _detector.TrySubmit(frame, width, ActiveFamilies(), probe: false);
    }

    private void TryAutoSelectFamily(IReadOnlyList<DetectedTag> tags)
    {
        if (!AutoProbeMode || tags.Count == 0)
            return;

        var tag = tags[0];
        if (_probeCandidateFamily == tag.Family && _probeCandidateId == tag.Id)
            _probeCandidateStreak++;
        else
        {
            _probeCandidateFamily = tag.Family;
            _probeCandidateId = tag.Id;
            _probeCandidateStreak = 1;
        }

        if (_probeCandidateStreak < 2)
            return;

        _selectedFamily = tag.Family;
        FamilyCombo.SelectedItem = tag.Family;
        _familyLocked = true;
        _probeFamilyIndex = 0;
        ApplyDetectorConfig();
        StatusText.Text =
            L.F("StatusFamilyDetected", TagFamilyCatalog.GetLabel(tag.Family), tag.Id);
    }

    private void DrawTags(Mat frame, IReadOnlyList<DetectedTag> tags)
    {
        var probing = AutoProbeMode;
        foreach (var tag in tags)
        {
            var dup = _session.Duplicates.Contains(tag.Key);
            var color = dup ? new Scalar(0, 0, 220) : probing ? new Scalar(255, 160, 0) : new Scalar(0, 220, 0);
            var pts = tag.Corners.Select(p => new OpenCvSharp.Point((int)p.X, (int)p.Y)).ToArray();
            for (var i = 0; i < 4; i++)
                Cv2.Line(frame, pts[i], pts[(i + 1) % 4], color, dup ? 3 : 2);

            var label = probing
                ? $"{tag.Id}?"
                : dup
                    ? $"{tag.Id} {L.S("OverlayDup")}"
                    : tag.Id.ToString();
            Cv2.PutText(frame, label, new OpenCvSharp.Point((int)tag.Center.X - 20, (int)tag.Center.Y + 6),
                HersheyFonts.HersheySimplex, 0.55, color, 2);
        }
    }

    private static BitmapSource MatToBitmap(Mat mat)
    {
        using var rgb = new Mat();
        Cv2.CvtColor(mat, rgb, ColorConversionCodes.BGR2RGB);
        var stride = rgb.Width * rgb.ElemSize();
        var bytes = new byte[stride * rgb.Height];
        Marshal.Copy(rgb.Data, bytes, 0, bytes.Length);
        var bmp = BitmapSource.Create(rgb.Width, rgb.Height, 96, 96, PixelFormats.Bgr24, null, bytes, stride);
        bmp.Freeze();
        return bmp;
    }

    private void UpdateCount(int inFrame)
    {
        var unique = _session.Records.Select(r => new TagKey(r.Family, r.Id)).Distinct().Count();
        _lastInFrame = inFrame;
        CountText.Text =
            L.F("CountLine", _session.Records.Count, unique, inFrame, _session.Duplicates.Count);
    }

    private void TrackFps(double frameMs, double detectMs)
    {
        _frameTimes.Enqueue(frameMs);
        while (_frameTimes.Count > 30)
            _frameTimes.Dequeue();
        var avg = _frameTimes.Average();
        var fps = avg > 0 ? 1000.0 / avg : 0;
        PerfText.Text =
            $"FPS: {fps:F1}  |  Detect: {detectMs:F0} ms  |  {SpeedPresetSettings.Label(_preset)}" +
            (AutoProbeMode ? $"  |  {L.S("PerfAuto")}" : "");
    }

    private void ReconnectButton_OnClick(object sender, RoutedEventArgs e)
    {
        _timer.Stop();
        _camera.Close();
        _currentCameraIndex = -1;
        RefreshCameraList(startCameraAfter: true);
    }

    private void CameraCombo_OnSelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        if (!IsLoaded || _scanning || _refreshingCameras || CameraCombo.SelectedItem is not CameraDevice camera)
            return;

        if (camera.IsPlaceholder)
            return;

        var index = camera.Index;
        if (index == _currentCameraIndex)
            return;

        _timer.Stop();
        _camera.Close();
        _currentCameraIndex = -1;

        Task.Run(async () =>
        {
            await Task.Delay(300);
            await Dispatcher.InvokeAsync(StartCamera);
        });
    }

    private void InitCameraCombo()
    {
        CameraCombo.ItemTemplate = CreateCameraItemTemplate();
    }

    private void RefreshCameraComboDisplay()
    {
        if (CameraCombo.ItemsSource is not IReadOnlyList<CameraDevice> cameras || cameras.Count == 0)
            return;

        var index = CameraCombo.SelectedItem is CameraDevice selected
            ? selected.Index
            : _currentCameraIndex;

        CameraCombo.SelectionChanged -= CameraCombo_OnSelectionChanged;
        try
        {
            CameraCombo.ItemTemplate = CreateCameraItemTemplate();
            CameraCombo.SelectedItem = cameras.FirstOrDefault(c => c.Index == index) ?? cameras[0];
        }
        finally
        {
            CameraCombo.SelectionChanged += CameraCombo_OnSelectionChanged;
        }
    }

    private void RefreshCameraList(bool startCameraAfter)
    {
        _refreshingCameras = true;
        CameraCombo.IsEnabled = false;
        ReconnectButton.IsEnabled = false;
        StatusText.Text = L.S("CameraSearching");

        var preferredIndex = GetSelectedCameraIndex();
        if (preferredIndex < 0)
            preferredIndex = _currentCameraIndex >= 0 ? _currentCameraIndex : 0;

        Task.Run(CameraEnumerator.Enumerate)
            .ContinueWith(task =>
            {
                var cameras = task.Status == TaskStatus.RanToCompletion
                    ? task.Result
                    : Array.Empty<CameraDevice>();

                Dispatcher.BeginInvoke(() =>
                {
                    try
                    {
                        if (cameras.Count == 0)
                        {
                            _currentCameraIndex = -1;
                            StartButton.IsEnabled = false;
                            ResetButton.IsEnabled = false;
                            CameraCombo.ItemsSource = new[] { CreateNoCameraPlaceholder() };
                            CameraCombo.SelectedIndex = 0;
                            StatusText.Text = L.S("CameraNoneFound");
                            MainTab.SelectedIndex = 1;
                            return;
                        }

                        CameraCombo.ItemsSource = cameras;
                        var selected = cameras.FirstOrDefault(c => c.Index == preferredIndex) ?? cameras[0];
                        CameraCombo.SelectedItem = selected;

                        if (startCameraAfter)
                        {
                            Task.Run(async () =>
                            {
                                await Task.Delay(600);
                                await Dispatcher.InvokeAsync(StartCamera);
                            });
                        }
                    }
                    finally
                    {
                        _refreshingCameras = false;
                        CameraCombo.IsEnabled = !_scanning;
                        ReconnectButton.IsEnabled = true;
                    }
                });
            });
    }

    private int GetSelectedCameraIndex()
    {
        if (CameraCombo.SelectedItem is CameraDevice camera)
            return camera.IsPlaceholder ? CameraDevice.NoCameraIndex : camera.Index;
        return CameraDevice.NoCameraIndex;
    }

    private static CameraDevice CreateNoCameraPlaceholder() =>
        new() { Index = CameraDevice.NoCameraIndex };

    private static DataTemplate CreateCameraItemTemplate()
    {
        var template = new DataTemplate(typeof(CameraDevice));
        var factory = new FrameworkElementFactory(typeof(System.Windows.Controls.TextBlock));
        factory.SetBinding(System.Windows.Controls.TextBlock.TextProperty, new System.Windows.Data.Binding
        {
            Converter = new CameraDeviceLabelConverter(),
        });
        template.VisualTree = factory;
        return template;
    }

    private sealed class CameraDeviceLabelConverter : System.Windows.Data.IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture) =>
            value is CameraDevice camera
                ? camera.IsPlaceholder
                    ? L.S("CameraNonePlaceholder")
                    : camera.Name.Length > 0
                        ? camera.Name
                        : L.F("CameraListItemIndex", camera.Index)
                : value?.ToString() ?? "";

        public object ConvertBack(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture) =>
            throw new NotSupportedException();
    }

    private void StartButton_OnClick(object sender, RoutedEventArgs e) => StartScan();

    private void StopButton_OnClick(object sender, RoutedEventArgs e) => StopScan();

    private void ResetButton_OnClick(object sender, RoutedEventArgs e) => ResetScan();

    private void StartScan()
    {
        if (!_familyLocked && MultiFamilyCheck.IsChecked != true)
        {
            _familyLocked = true;
            ApplyDetectorConfig();
        }

        _scanning = true;
        _session.ClearTracking();
        StatusText.Text = L.S("StatusScanning");
        StartButton.IsEnabled = false;
        StopButton.IsEnabled = true;
        SaveButton.IsEnabled = false;
        SetSettingsEnabled(false);
    }

    private void StopScan()
    {
        _scanning = false;
        _session.ClearTracking();
        StartButton.IsEnabled = true;
        StopButton.IsEnabled = false;
        SaveButton.IsEnabled = true;
        SetSettingsEnabled(true);

        var report = ExportHelper.BuildTextReport(_session, FamiliesDescription(), DateTime.Now);
        ResultBox.Text = report;

        var summary = _session.Duplicates.Count > 0
            ? L.F("StatusDoneDup", string.Join(", ", _session.Duplicates.Select(d => d.Id.ToString())))
            : L.S("StatusDoneNoDup");
        StatusText.Text = summary;
        MessageBox.Show(summary, L.ResultTitle,
            MessageBoxButton.OK,
            _session.Duplicates.Count > 0 ? MessageBoxImage.Warning : MessageBoxImage.Information);
    }

    private void ResetScan()
    {
        _scanning = false;
        _session.Reset();
        _liveLines.Clear();
        ResultBox.Clear();
        _familyLocked = false;
        _probeFamilyIndex = 0;
        _probeCandidateStreak = 0;
        ApplyDetectorConfig();
        StatusText.Text = L.S("StatusShowTag");
        UpdateCount(0);
        StartButton.IsEnabled = true;
        StopButton.IsEnabled = false;
        SaveButton.IsEnabled = false;
        SetSettingsEnabled(true);
    }

    private void SaveButton_OnClick(object sender, RoutedEventArgs e) => SaveResults();

    private void SaveResults()
    {
        if (!SaveButton.IsEnabled)
            return;

        var dlg = new SaveFileDialog
        {
            Title = L.S("SaveDialogTitle"),
            Filter = L.S("SaveDialogFilter"),
            FileName = $"apriltag_scan_{DateTime.Now:yyyyMMdd_HHmmss}.txt",
        };
        if (dlg.ShowDialog() != true)
            return;

        try
        {
            ExportHelper.Save(dlg.FileName, _session, FamiliesDescription());
            MessageBox.Show(L.F("SaveSuccess", dlg.FileName), L.SavedTitle);
        }
        catch (Exception ex)
        {
            MessageBox.Show(L.F("SaveFailed", ex.Message), L.ErrorTitle, MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void FamilyCombo_OnSelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        if (FamilyCombo.SelectedItem is not string family || _scanning)
            return;
        _selectedFamily = family;
        _familyLocked = true;
        ApplyDetectorConfig();
        StatusText.Text = L.F("StatusFamilyManual", TagFamilyCatalog.GetLabel(family));
    }

    private void MultiFamilyCheck_OnChanged(object sender, RoutedEventArgs e)
    {
        if (_scanning)
            return;
        _familyLocked = MultiFamilyCheck.IsChecked == true;
        if (MultiFamilyCheck.IsChecked != true)
            _familyLocked = false;
        ApplyDetectorConfig();
        StatusText.Text = MultiFamilyCheck.IsChecked == true
            ? L.S("StatusMultiFamily")
            : L.S("StatusShowTag");
    }

    private void PresetCombo_OnSelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        if (_applyingLocalization || PresetCombo.SelectedItem is not SpeedPreset preset || _scanning)
            return;
        _preset = preset;
        ApplyDetectorConfig();
    }

    private void SetSettingsEnabled(bool enabled)
    {
        FamilyCombo.IsEnabled = enabled;
        PresetCombo.IsEnabled = enabled;
        MultiFamilyCheck.IsEnabled = enabled;
        CameraCombo.IsEnabled = enabled;
        MissBox.IsEnabled = enabled;
        BeepCheck.IsEnabled = enabled;
    }

    private void MainWindow_OnKeyDown(object sender, KeyEventArgs e)
    {
        if (MainTab.SelectedIndex != 0)
            return;

        if (e.Key == Key.Space)
        {
            if (_scanning)
                StopScan();
            else if (StartButton.IsEnabled)
                StartScan();
            e.Handled = true;
        }
        else if (Keyboard.Modifiers == ModifierKeys.Control && e.Key == Key.S)
        {
            SaveResults();
            e.Handled = true;
        }
        else if (Keyboard.Modifiers == ModifierKeys.Control && e.Key == Key.R)
        {
            ResetScan();
            e.Handled = true;
        }
    }

    private static int ParseInt(string text, int fallback) =>
        int.TryParse(text, out var value) ? value : fallback;

    private void Shutdown()
    {
        CancelGeneratorPreview();
        _timer.Stop();
        _camera.Dispose();
        _detector.Dispose();
    }
}
