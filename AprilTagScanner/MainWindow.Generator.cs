using System.IO;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using AprilTagScanner.Localization;
using AprilTagScanner.Services;
using Microsoft.Win32;

namespace AprilTagScanner;

public partial class MainWindow
{
    private bool _genInputGuard;
    private bool _genHasCorrectionMessage;
    private CancellationTokenSource? _previewCts;
    private int _previewGeneration;
    private bool _genExportRunning;
    private readonly DispatcherTimer _previewDebounce = new() { Interval = TimeSpan.FromMilliseconds(300) };

    private void InitGeneratorTab()
    {
        _previewDebounce.Tick += (_, _) =>
        {
            _previewDebounce.Stop();
            RunGeneratorPreviewAsync();
        };

        foreach (var family in TagFamilyCatalog.AllFamilies)
            GenFamilyCombo.Items.Add(family);
        GenFamilyCombo.SelectedItem = "tag36h11";

        GenPageFormatCombo.Items.Add(PageFormat.A4);
        GenPageFormatCombo.SelectedItem = PageFormat.A4;

        GenTagsPerPageCombo.Items.Add(1);
        GenTagsPerPageCombo.Items.Add(6);
        GenTagsPerPageCombo.SelectedItem = 6;

        UpdateGeneratorRangeHint();
        RefreshGeneratorUi();
    }

    private void MainTab_OnSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!IsLoaded)
            return;

        if (MainTab.SelectedIndex == 0)
        {
            CancelGeneratorPreview();
            if (_timer.IsEnabled == false)
                _timer.Start();
            return;
        }

        _timer.Stop();
        ScheduleGeneratorPreview();
    }

    private void GenFamilyCombo_OnSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!IsLoaded || _genInputGuard)
            return;

        UpdateGeneratorRangeHint();
        ConstrainGeneratorInputs(notify: true);
        RefreshGeneratorUi();
    }

    private void GenSettings_OnChanged(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded)
            return;

        RefreshGeneratorUi();
    }

    private void GenNumeric_PreviewTextInput(object sender, TextCompositionEventArgs e)
    {
        e.Handled = !Regex.IsMatch(e.Text, "^[0-9]+$");
    }

    private void GenNumeric_OnChanged(object sender, TextChangedEventArgs e)
    {
        if (!IsLoaded || _genInputGuard)
            return;

        RefreshGeneratorUi(liveOnly: true);
    }

    private void GenNumeric_OnLostFocus(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded || _genInputGuard)
            return;

        ConstrainGeneratorInputs(notify: true);
        RefreshGeneratorUi();
    }

    private void UpdateGeneratorRangeHint()
    {
        if (GenFamilyCombo.SelectedItem is not string family)
            return;

        GenRangeText.Text = L.F(
            "GenAllowedId",
            TagGeneratorService.FormatIdRange(family),
            TagFamilyCatalog.GetLabel(family));
    }

    private void RefreshGeneratorUi(bool liveOnly = false)
    {
        if (!TryReadGeneratorSettings(out var settings, out var error))
        {
            GenInfoText.Text = error;
            GenInfoText.Foreground = new SolidColorBrush(Color.FromRgb(0xCC, 0x00, 0x00));
            GenStatusText.Text = error;
            GenExportButton.IsEnabled = false;
            GenPreviewImage.Source = null;
            return;
        }

        GenInfoText.Foreground = new SolidColorBrush(Colors.Black);
        var pages = (settings.Count + settings.TagsPerPage - 1) / settings.TagsPerPage;
        var lastId = settings.StartId + settings.Count - 1;
        GenInfoText.Text = L.F("GenSummary", settings.Count, settings.StartId, lastId, pages);
        GenExportButton.IsEnabled = true;

        if (liveOnly)
            return;

        if (MainTab.SelectedIndex == 1)
            ScheduleGeneratorPreview();
        else if (!_genHasCorrectionMessage)
            GenStatusText.Text = "";
    }

    private void ConstrainGeneratorInputs(bool notify)
    {
        if (GenFamilyCombo.SelectedItem is not string family)
            return;

        var maxId = TagGeneratorService.GetMaxId(family);
        var label = TagFamilyCatalog.GetLabel(family);
        var startId = ParseGenInt(GenStartIdBox.Text, 0);
        var count = ParseGenInt(GenCountBox.Text, 1);
        string? message = null;
        var changed = false;

        if (string.IsNullOrWhiteSpace(GenStartIdBox.Text))
        {
            startId = 0;
            SetGenText(GenStartIdBox, "0");
            changed = true;
        }

        if (startId > maxId)
        {
            message = L.F("GenMaxIdFixed", label, maxId);
            startId = maxId;
            SetGenText(GenStartIdBox, startId.ToString());
            changed = true;
        }

        var maxCount = maxId - startId + 1;
        if (string.IsNullOrWhiteSpace(GenCountBox.Text))
        {
            count = 1;
            SetGenText(GenCountBox, "1");
            changed = true;
        }

        if (count < 1)
        {
            message = L.S("GenCountMinFixed");
            count = 1;
            SetGenText(GenCountBox, "1");
            changed = true;
        }
        else if (count > maxCount)
        {
            message = L.F("GenCountMaxFixed", startId, maxCount, maxId);
            count = maxCount;
            SetGenText(GenCountBox, count.ToString());
            changed = true;
        }

        if (notify && changed && message != null)
        {
            _genHasCorrectionMessage = true;
            GenStatusText.Text = message;
        }
    }

    private void SetGenText(TextBox box, string value)
    {
        if (box.Text == value)
            return;

        _genInputGuard = true;
        box.Text = value;
        box.CaretIndex = value.Length;
        _genInputGuard = false;
    }

    private static int ParseGenInt(string text, int fallback) =>
        int.TryParse(text, out var value) ? value : fallback;

    private void ScheduleGeneratorPreview()
    {
        if (!IsLoaded || MainTab.SelectedIndex != 1)
            return;

        _previewDebounce.Stop();
        _previewDebounce.Start();
    }

    private void RunGeneratorPreviewAsync()
    {
        _previewCts?.Cancel();
        _previewCts?.Dispose();
        _previewCts = new CancellationTokenSource();
        var token = _previewCts.Token;
        var generation = Interlocked.Increment(ref _previewGeneration);

        if (!TryReadGeneratorSettings(out var settings, out _))
        {
            GenPreviewImage.Source = null;
            return;
        }

        if (!_genHasCorrectionMessage)
            GenStatusText.Text = L.S("GenPreviewWorking");

        var previewSettings = settings;
        Task.Run(() =>
        {
            token.ThrowIfCancellationRequested();
            return TagPdfExporter.RenderFirstPagePreview(
                previewSettings.Family,
                previewSettings.StartId,
                previewSettings.Count,
                previewSettings.TagsPerPage,
                previewSettings.PageFormat);
        }, token).ContinueWith(t =>
        {
            Dispatcher.BeginInvoke(() =>
            {
                if (generation != _previewGeneration || MainTab.SelectedIndex != 1)
                    return;

                if (t.IsCanceled)
                    return;

                if (t.IsFaulted)
                {
                    GenPreviewImage.Source = null;
                    GenStatusText.Text = L.F(
                        "GenPreviewFailed",
                        t.Exception?.GetBaseException().Message ?? "unknown");
                    return;
                }

                try
                {
                    GenPreviewImage.Source = PngBytesToBitmap(t.Result);
                    if (!_genHasCorrectionMessage)
                        GenStatusText.Text = L.S("GenPreview");
                }
                catch (Exception ex)
                {
                    GenPreviewImage.Source = null;
                    GenStatusText.Text = L.F("GenPreviewFailed", ex.Message);
                }
            });
        }, TaskScheduler.Default);
    }

    private void CancelGeneratorPreview()
    {
        _previewDebounce.Stop();
        _previewCts?.Cancel();
        _previewCts?.Dispose();
        _previewCts = null;
        Interlocked.Increment(ref _previewGeneration);
    }

    private void GenExportButton_OnClick(object sender, RoutedEventArgs e)
    {
        if (_genExportRunning)
            return;

        ConstrainGeneratorInputs(notify: true);
        if (!TryReadGeneratorSettings(out var settings, out var error))
        {
            MessageBox.Show(error, L.GeneratorTitleDlg, MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var familyShort = settings.Family.Replace("tag", "", StringComparison.Ordinal);
        var dlg = new SaveFileDialog
        {
            Title = L.S("GenPdfDialogTitle"),
            Filter = L.S("GenPdfDialogFilter"),
            FileName = $"apriltag_{familyShort}_{settings.StartId}_{settings.Count}_{DateTime.Now:yyyyMMdd_HHmmss}.pdf",
        };

        if (dlg.ShowDialog() != true)
            return;

        var path = dlg.FileName;
        _genExportRunning = true;
        GenExportButton.IsEnabled = false;
        GenStatusText.Text = L.S("GenPdfWorking");

        Task.Run(() =>
        {
            TagPdfExporter.Export(
                path,
                settings.Family,
                settings.StartId,
                settings.Count,
                settings.TagsPerPage,
                settings.PageFormat);
        }).ContinueWith(t =>
        {
            Dispatcher.BeginInvoke(() =>
            {
                _genExportRunning = false;
                GenExportButton.IsEnabled = TryReadGeneratorSettings(out _, out _);

                if (t.IsFaulted)
                {
                    MessageBox.Show(
                        L.F("GenPdfSaveFailed", t.Exception?.GetBaseException().Message ?? "unknown"),
                        L.ErrorTitle,
                        MessageBoxButton.OK,
                        MessageBoxImage.Error);
                    return;
                }

                _genHasCorrectionMessage = false;
                GenStatusText.Text = L.F("GenPdfSaved", Path.GetFileName(path));
                MessageBox.Show(L.F("GenPdfSaveSuccess", path), L.GeneratorTitleDlg,
                    MessageBoxButton.OK, MessageBoxImage.Information);
            });
        }, TaskScheduler.Default);
    }

    private bool TryReadGeneratorSettings(out GeneratorSettings settings, out string error)
    {
        settings = default!;
        error = "";

        if (GenFamilyCombo.SelectedItem is not string family)
        {
            error = L.S("ValSelectFamily");
            return false;
        }

        if (string.IsNullOrWhiteSpace(GenCountBox.Text) || string.IsNullOrWhiteSpace(GenStartIdBox.Text))
        {
            error = L.S("ValEnterCountStart");
            return false;
        }

        if (!int.TryParse(GenStartIdBox.Text, out var startId))
        {
            error = L.S("ValStartIdInteger");
            return false;
        }

        if (!int.TryParse(GenCountBox.Text, out var count))
        {
            error = L.S("ValCountInteger");
            return false;
        }

        var maxId = TagGeneratorService.GetMaxId(family);
        var label = TagFamilyCatalog.GetLabel(family);

        if (startId < 0)
        {
            error = L.S("ValStartIdNegative");
            return false;
        }

        if (startId > maxId)
        {
            error = L.F("ValStartIdTooBig", startId, maxId, label);
            return false;
        }

        if (count < 1)
        {
            error = L.S("ValCountMin");
            return false;
        }

        var lastId = startId + count - 1;
        if (lastId > maxId)
        {
            error = L.F("ValRangeOverflow", startId, lastId, label, maxId);
            return false;
        }

        var tagsPerPage = ReadTagsPerPage(GenTagsPerPageCombo);
        var pageFormat = GenPageFormatCombo.SelectedItem is PageFormat format ? format : PageFormat.A4;
        settings = new GeneratorSettings(family, count, startId, tagsPerPage, pageFormat);
        return true;
    }

    private static int ReadTagsPerPage(ComboBox combo) =>
        combo.SelectedItem switch
        {
            int value => value,
            string text when int.TryParse(text, out var parsed) => parsed,
            _ => 6,
        };

    private static BitmapSource PngBytesToBitmap(byte[] png)
    {
        using var stream = new MemoryStream(png);
        var image = new BitmapImage();
        image.BeginInit();
        image.CacheOption = BitmapCacheOption.OnLoad;
        image.StreamSource = stream;
        image.EndInit();
        image.Freeze();
        return image;
    }

    private readonly record struct GeneratorSettings(
        string Family,
        int Count,
        int StartId,
        int TagsPerPage,
        PageFormat PageFormat);
}
