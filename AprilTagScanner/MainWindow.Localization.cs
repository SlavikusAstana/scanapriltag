using System.Windows;
using System.Windows.Controls;
using AprilTagScanner.Localization;
using AprilTagScanner.Services;

namespace AprilTagScanner;

public partial class MainWindow
{
    private int _lastInFrame;
    private bool _applyingLocalization;

    private void InitLanguageSelector()
    {
        LanguageCombo.ItemsSource = new[] { AppLanguage.Russian, AppLanguage.English };
        LanguageCombo.ItemTemplate = CreateLanguageItemTemplate();
        LanguageCombo.SelectedItem = L.Current;
    }

    private void LanguageCombo_OnSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!IsLoaded || _applyingLocalization || LanguageCombo.SelectedItem is not AppLanguage language)
            return;

        if (language == L.Current)
            return;

        L.SetLanguage(language);
        ApplyLocalization();
    }

    private void ApplyLocalization()
    {
        if (_applyingLocalization)
            return;

        _applyingLocalization = true;
        try
        {
            ApplyLocalizationCore();
        }
        finally
        {
            _applyingLocalization = false;
        }
    }

    private void ApplyLocalizationCore()
    {
        Title = L.AppTitle;
        ScannerTab.Header = L.TabScanner;
        GeneratorTab.Header = L.TabGenerator;
        LanguageLabel.Text = L.LanguageLabel;

        AppTitleText.Text = L.AppTitle;
        SettingsGroup.Header = L.SettingsGroup;
        FamilyLabel.Text = L.FamilyAuto;
        MultiFamilyCheck.Content = L.MultiFamily;
        SpeedLabel.Text = L.Speed;
        CameraLabel.Text = L.Camera;
        MissLabel.Text = L.Miss;
        BeepCheck.Content = L.BeepOnDuplicate;
        ReconnectButton.Content = L.ReconnectCamera;
        StartButton.Content = L.Start;
        StopButton.Content = L.Stop;
        ResetButton.Content = L.Reset;
        SaveButton.Content = L.Save;
        LiveListLabel.Text = L.LiveList;
        ResultLabel.Text = L.ResultAfterStop;
        HotkeysText.Text = L.Hotkeys;

        GeneratorTitleText.Text = L.GeneratorTitle;
        ParametersGroup.Header = L.ParametersGroup;
        GenFamilyLabel.Text = L.Family;
        GenCountLabel.Text = L.Count;
        GenStartIdLabel.Text = L.StartId;
        GenPageFormatLabel.Text = L.PageFormat;
        GenTagsPerPageLabel.Text = L.TagsPerPage;
        GenExportButton.Content = L.SavePdf;
        GeneratorHintText.Text = L.GeneratorHint;

        RefreshPresetComboDisplay();
        RefreshCameraComboDisplay();
        ApplyDetectorConfig();
        RefreshStatusForLanguage();
        RefreshLiveListLanguage();
        if (_session.Records.Count > 0 && !string.IsNullOrWhiteSpace(ResultBox.Text))
            ResultBox.Text = ExportHelper.BuildTextReport(_session, FamiliesDescription(), DateTime.Now);
        UpdateCount(_lastInFrame);
        UpdateGeneratorRangeHint();
        RefreshGeneratorUi();
    }

    private static DataTemplate CreateLanguageItemTemplate()
    {
        var template = new DataTemplate(typeof(AppLanguage));
        var factory = new FrameworkElementFactory(typeof(TextBlock));
        factory.SetBinding(TextBlock.TextProperty, new System.Windows.Data.Binding
        {
            Converter = new LanguageNameConverter(),
        });
        template.VisualTree = factory;
        return template;
    }

    private void InitPresetCombo()
    {
        PresetCombo.ItemsSource = new[] { SpeedPreset.Fast, SpeedPreset.Balanced, SpeedPreset.Accurate };
        PresetCombo.ItemTemplate = CreatePresetItemTemplate();
        PresetCombo.SelectedItem = SpeedPreset.Balanced;
    }

    private void RefreshPresetComboDisplay()
    {
        var selected = PresetCombo.SelectedItem as SpeedPreset? ?? _preset;
        PresetCombo.SelectionChanged -= PresetCombo_OnSelectionChanged;
        try
        {
            PresetCombo.ItemTemplate = CreatePresetItemTemplate();
            PresetCombo.SelectedItem = selected;
        }
        finally
        {
            PresetCombo.SelectionChanged += PresetCombo_OnSelectionChanged;
        }
    }

    private static DataTemplate CreatePresetItemTemplate()
    {
        var template = new DataTemplate(typeof(SpeedPreset));
        var factory = new FrameworkElementFactory(typeof(TextBlock));
        factory.SetBinding(TextBlock.TextProperty, new System.Windows.Data.Binding
        {
            Converter = new PresetLabelConverter(),
        });
        template.VisualTree = factory;
        return template;
    }

    private void RefreshLiveListLanguage()
    {
        if (_liveLines.Count == 0)
            return;

        for (var i = 0; i < _session.Records.Count && i < _liveLines.Count; i++)
        {
            var record = _session.Records[i];
            _liveLines[i] = new LiveLine
            {
                Text = $"{i + 1}. {record.Label}{(record.Duplicate ? L.S("DuplicateMark") : "")}",
                Duplicate = record.Duplicate,
            };
        }
    }

    private void RefreshStatusForLanguage()
    {
        if (_scanning)
        {
            StatusText.Text = L.S("StatusScanning");
            return;
        }

        if (AutoProbeMode && !_familyLocked)
        {
            StatusText.Text = L.S("StatusShowTag");
            return;
        }

        if (MultiFamilyCheck.IsChecked == true && _familyLocked)
        {
            StatusText.Text = L.S("StatusMultiFamily");
            return;
        }

        if (_familyLocked && FamilyCombo.SelectedItem is string family)
        {
            StatusText.Text = L.F("StatusFamilyManual", TagFamilyCatalog.GetLabel(family));
        }
    }

    private sealed class LanguageNameConverter : System.Windows.Data.IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture) =>
            value is AppLanguage language ? L.LanguageName(language) : value?.ToString() ?? "";

        public object ConvertBack(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture) =>
            throw new NotSupportedException();
    }

    private sealed class PresetLabelConverter : System.Windows.Data.IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture) =>
            value is SpeedPreset preset ? SpeedPresetSettings.Label(preset) : value?.ToString() ?? "";

        public object ConvertBack(object value, Type targetType, object parameter, System.Globalization.CultureInfo culture) =>
            throw new NotSupportedException();
    }
}
