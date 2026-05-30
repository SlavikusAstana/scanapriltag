namespace AprilTagScanner.Localization;

public static class L
{
    public static AppLanguage Current { get; private set; } = AppLanguage.Russian;

    public static event Action? Changed;

    public static void Initialize(AppLanguage language) => SetLanguage(language, persist: false);

    public static void SetLanguage(AppLanguage language, bool persist = true)
    {
        if (Current == language)
            return;

        Current = language;
        if (persist)
            LanguageSettings.Save(language);
        Changed?.Invoke();
    }

    public static string LanguageName(AppLanguage language) => language switch
    {
        AppLanguage.Russian => "Русский",
        AppLanguage.English => "English",
        _ => language.ToString(),
    };

    public static string F(string key, params object[] args) =>
        string.Format(S(key), args);

    public static string S(string key) =>
        Table.TryGetValue((Current, key), out var value) ? value : key;

    // --- UI labels ---
    public static string AppTitle => S("AppTitle");
    public static string TabScanner => S("TabScanner");
    public static string TabGenerator => S("TabGenerator");
    public static string LanguageLabel => S("LanguageLabel");
    public static string SettingsGroup => S("SettingsGroup");
    public static string FamilyAuto => S("FamilyAuto");
    public static string MultiFamily => S("MultiFamily");
    public static string Speed => S("Speed");
    public static string Camera => S("Camera");
    public static string Miss => S("Miss");
    public static string BeepOnDuplicate => S("BeepOnDuplicate");
    public static string ReconnectCamera => S("ReconnectCamera");
    public static string Start => S("Start");
    public static string Stop => S("Stop");
    public static string Reset => S("Reset");
    public static string Save => S("Save");
    public static string LiveList => S("LiveList");
    public static string ResultAfterStop => S("ResultAfterStop");
    public static string Hotkeys => S("Hotkeys");
    public static string GeneratorTitle => S("GeneratorTitle");
    public static string ParametersGroup => S("ParametersGroup");
    public static string Family => S("Family");
    public static string Count => S("Count");
    public static string StartId => S("StartId");
    public static string PageFormat => S("PageFormat");
    public static string TagsPerPage => S("TagsPerPage");
    public static string SavePdf => S("SavePdf");
    public static string GeneratorHint => S("GeneratorHint");
    public static string ErrorTitle => S("ErrorTitle");
    public static string ResultTitle => S("ResultTitle");
    public static string SavedTitle => S("SavedTitle");
    public static string GeneratorTitleDlg => S("GeneratorTitleDlg");

    // --- Speed presets ---
    public static string PresetFast => S("PresetFast");
    public static string PresetBalanced => S("PresetBalanced");
    public static string PresetAccurate => S("PresetAccurate");

    // --- Family labels ---
    public static string Family36h11 => S("Family36h11");
    public static string Family25h9 => S("Family25h9");
    public static string Family16h5 => S("Family16h5");
    public static string Family36h10 => S("Family36h10");

    public static string FamilyLabel(string family) => family switch
    {
        "tag36h11" => Family36h11,
        "tag25h9" => Family25h9,
        "tag16h5" => Family16h5,
        "tag36h10" => Family36h10,
        _ => family.Replace("tag", "", StringComparison.Ordinal),
    };

    private static readonly Dictionary<(AppLanguage, string), string> Table = Build();

    private static Dictionary<(AppLanguage, string), string> Build()
    {
        var d = new Dictionary<(AppLanguage, string), string>();

        void Add(AppLanguage lang, string key, string value) => d[(lang, key)] = value;

        foreach (var (key, ru, en) in Entries)
        {
            Add(AppLanguage.Russian, key, ru);
            Add(AppLanguage.English, key, en);
        }

        return d;
    }

    private static IEnumerable<(string Key, string Ru, string En)> Entries =>
    [
        ("AppTitle", "AprilTag Scanner Pro", "AprilTag Scanner Pro"),
        ("TabScanner", "Сканер", "Scanner"),
        ("TabGenerator", "Генератор", "Generator"),
        ("LanguageLabel", "Язык:", "Language:"),
        ("SettingsGroup", "Настройки", "Settings"),
        ("FamilyAuto", "Семейство (авто):", "Family (auto):"),
        ("MultiFamily", "Несколько семейств (36h11+25h9+16h5)", "Multiple families (36h11+25h9+16h5)"),
        ("Speed", "Скорость:", "Speed:"),
        ("Camera", "Камера:", "Camera:"),
        ("CameraSearching", "Поиск камер...", "Searching cameras..."),
        ("CameraListItem", "Камера {0}: {1}", "Camera {0}: {1}"),
        ("CameraListItemIndex", "Камера {0}", "Camera {0}"),
        ("CameraNoneFound",
            "Камера не найдена — сканер недоступен. Вкладка «Генератор» работает без камеры. Нажмите «Переподключить» после подключения.",
            "No camera found — scanner unavailable. The Generator tab works without a camera. Click Reconnect after connecting one."),
        ("CameraNonePlaceholder", "Нет камер", "No cameras"),
        ("CameraOpenFailedStatus",
            "Не удалось подключить камеру {0}: {1}. Выберите другую или используйте «Генератор».",
            "Could not connect camera {0}: {1}. Select another one or use the Generator tab."),
        ("CameraErrorStatus", "Ошибка камеры: {0}. Можно работать во вкладке «Генератор».",
            "Camera error: {0}. You can use the Generator tab."),
        ("Miss", "Miss:", "Miss:"),
        ("BeepOnDuplicate", "Звук при повторе", "Beep on duplicate"),
        ("ReconnectCamera", "Переподключить камеру", "Reconnect camera"),
        ("Start", "Старт", "Start"),
        ("Stop", "Стоп", "Stop"),
        ("Reset", "Сброс", "Reset"),
        ("Save", "Сохранить (Ctrl+S)", "Save (Ctrl+S)"),
        ("LiveList", "Список (live):", "List (live):"),
        ("ResultAfterStop", "Результат после «Стоп»:", "Result after Stop:"),
        ("Hotkeys", "Space — старт/стоп  |  Ctrl+S — сохранить  |  Ctrl+R — сброс",
            "Space — start/stop  |  Ctrl+S — save  |  Ctrl+R — reset"),
        ("GeneratorTitle", "Генератор AprilTag", "AprilTag Generator"),
        ("ParametersGroup", "Параметры", "Parameters"),
        ("Family", "Семейство:", "Family:"),
        ("Count", "Количество:", "Count:"),
        ("StartId", "Стартовый ID:", "Start ID:"),
        ("PageFormat", "Формат страницы:", "Page format:"),
        ("TagsPerPage", "Тегов на листе:", "Tags per page:"),
        ("SavePdf", "Сохранить PDF", "Save PDF"),
        ("GeneratorHint",
            "При 6 тегах номер над тегом, при 1 — под ним. Печатайте в масштабе 100%, без «подогнать под страницу».",
            "With 6 tags the ID is above the tag; with 1 tag it is below. Print at 100% scale, not “fit to page”."),
        ("ErrorTitle", "Ошибка", "Error"),
        ("CrashUi", "Произошла ошибка:\n{0}", "An error occurred:\n{0}"),
        ("ResultTitle", "Результат", "Result"),
        ("SavedTitle", "Сохранено", "Saved"),
        ("GeneratorTitleDlg", "Генератор", "Generator"),
        ("PresetFast", "Быстро", "Fast"),
        ("PresetBalanced", "Баланс", "Balanced"),
        ("PresetAccurate", "Точно", "Accurate"),
        ("Family36h11", "36h11 (стандарт)", "36h11 (standard)"),
        ("Family25h9", "25h9", "25h9"),
        ("Family16h5", "16h5", "16h5"),
        ("Family36h10", "36h10", "36h10"),
        ("TitleAutoDetect", "AprilTag Scanner Pro — автоопределение", "AprilTag Scanner Pro — auto-detect"),
        ("PerfAuto", "авто", "auto"),
        ("OverlayDup", "DUP", "DUP"),
        ("DuplicateMark", "  [ПОВТОР]", "  [DUP]"),
        ("DuplicateMarkExport", " (повтор)", " (duplicate)"),

        ("CameraConnecting", "Подключение камеры...", "Connecting camera..."),
        ("CameraErrorGeneric", "Ошибка камеры:\n{0}", "Camera error:\n{0}"),
        ("CameraErrorRestart", "Ошибка камеры — выберите другую камеру и нажмите «Переподключить»",
            "Camera error — select another camera and click Reconnect"),
        ("CameraOpenFailed",
            "Не удалось открыть камеру {0}.\n{1}\n\nВыберите другую камеру в списке и нажмите «Переподключить».",
            "Could not open camera {0}.\n{1}\n\nSelect another camera from the list and click Reconnect."),
        ("CameraUnavailable", "Камера недоступна — выберите другую и нажмите «Переподключить»",
            "Camera unavailable — select another camera and click Reconnect"),
        ("CameraReady", "Камера {0} ({1}) — покажите тег для автоопределения семейства",
            "Camera {0} ({1}) — show a tag to auto-detect the family"),
        ("CameraTimeout", "Таймаут подключения камеры (10 сек). Закройте другие программы с камерой.",
            "Camera connection timed out (10 sec). Close other apps using the camera."),
        ("CameraNotResponding", "Камера не отвечает", "Camera is not responding"),

        ("StatusDuplicate", "ПОВТОР! {0} — отложите этот тег", "DUPLICATE! {0} — set this tag aside"),
        ("StatusFamilyDetected",
            "Определено: {0}, ID {1} — нажмите «Старт» (или Space)",
            "Detected: {0}, ID {1} — press Start (or Space)"),
        ("StatusScanning", "Сканирование — показывайте лист с тегами",
            "Scanning — show the sheet with tags"),
        ("StatusDoneDup", "Готово. Повторы есть: {0}", "Done. Duplicates: {0}"),
        ("StatusDoneNoDup", "Готово. Повторов нет.", "Done. No duplicates."),
        ("StatusShowTag", "Покажите тег камере — семейство определится автоматически",
            "Show a tag to the camera — the family will be detected automatically"),
        ("StatusFamilyManual", "Семейство: {0} — нажмите «Старт»", "Family: {0} — press Start"),
        ("StatusMultiFamily", "Режим нескольких семейств — нажмите «Старт»",
            "Multiple families mode — press Start"),

        ("CountLine", "Записано: {0}  |  Уник.: {1}  |  В кадре: {2}  |  Повторов: {3}",
            "Recorded: {0}  |  Unique: {1}  |  In frame: {2}  |  Duplicates: {3}"),

        ("SaveDialogTitle", "Сохранить результат", "Save result"),
        ("SaveDialogFilter", "Текст (*.txt)|*.txt|CSV (*.csv)|*.csv|JSON (*.json)|*.json",
            "Text (*.txt)|*.txt|CSV (*.csv)|*.csv|JSON (*.json)|*.json"),
        ("SaveSuccess", "Результат сохранён:\n{0}", "Result saved:\n{0}"),
        ("SaveFailed", "Не удалось сохранить файл:\n{0}", "Could not save file:\n{0}"),

        ("GenAllowedId", "Допустимый ID: {0} ({1})", "Allowed ID: {0} ({1})"),
        ("GenSummary", "Будет создано {0} тег(ов), ID {1}…{2}, страниц: {3}",
            "Will create {0} tag(s), ID {1}…{2}, pages: {3}"),
        ("GenPreview", "Предпросмотр первой страницы", "First page preview"),
        ("GenPreviewWorking", "Построение предпросмотра…", "Building preview…"),
        ("GenPdfWorking", "Сохранение PDF…", "Saving PDF…"),
        ("GenPreviewFailed", "Не удалось построить предпросмотр: {0}", "Could not build preview: {0}"),
        ("GenPdfSaved", "PDF сохранён: {0}", "PDF saved: {0}"),
        ("GenPdfSaveSuccess", "PDF сохранён:\n{0}", "PDF saved:\n{0}"),
        ("GenPdfSaveFailed", "Не удалось сохранить PDF:\n{0}", "Could not save PDF:\n{0}"),
        ("GenPdfDialogTitle", "Сохранить AprilTag PDF", "Save AprilTag PDF"),
        ("GenPdfDialogFilter", "PDF (*.pdf)|*.pdf", "PDF (*.pdf)|*.pdf"),
        ("GenMaxIdFixed", "Максимальный ID для {0} — {1}. Значение исправлено.",
            "Maximum ID for {0} is {1}. Value corrected."),
        ("GenCountMinFixed", "Количество тегов должно быть не меньше 1.",
            "Tag count must be at least 1."),
        ("GenCountMaxFixed",
            "При стартовом ID {0} можно создать не больше {1} тег(ов) (до ID {2}). Значение исправлено.",
            "With start ID {0} you can create at most {1} tag(s) (up to ID {2}). Value corrected."),

        ("ValSelectFamily", "Выберите семейство тегов.", "Select a tag family."),
        ("ValEnterCountStart", "Введите количество и стартовый ID.", "Enter count and start ID."),
        ("ValStartIdInteger", "Стартовый ID должен быть целым числом.", "Start ID must be an integer."),
        ("ValCountInteger", "Количество должно быть целым числом.", "Count must be an integer."),
        ("ValStartIdNegative", "Стартовый ID не может быть отрицательным.", "Start ID cannot be negative."),
        ("ValStartIdTooBig", "Стартовый ID {0} больше максимума ({1}) для {2}.",
            "Start ID {0} exceeds the maximum ({1}) for {2}."),
        ("ValCountMin", "Количество тегов должно быть не меньше 1.", "Tag count must be at least 1."),
        ("ValRangeOverflow",
            "Диапазон ID {0}…{1} выходит за пределы словаря. Максимальный ID для {2} — {3}.",
            "ID range {0}…{1} exceeds the dictionary. Maximum ID for {2} is {3}."),
        ("ValStartIdTooBigFamily", "Стартовый ID слишком большой. Для {0} максимум {1}.",
            "Start ID is too large. Maximum for {0} is {1}."),
        ("ValRangeDict", "Диапазон выходит за пределы словаря. Последний ID будет {0}, максимум {1}.",
            "Range exceeds the dictionary. Last ID would be {0}, maximum is {1}."),

        ("ExportTitle", "AprilTag Scanner Pro", "AprilTag Scanner Pro"),
        ("ExportDate", "Дата: {0:yyyy-MM-dd HH:mm:ss}", "Date: {0:yyyy-MM-dd HH:mm:ss}"),
        ("ExportFamilies", "Семейства: {0}", "Families: {0}"),
        ("ExportEmpty", "Список пуст — теги не обнаружены.", "List is empty — no tags detected."),
        ("ExportTotal", "Всего записано: {0}", "Total recorded: {0}"),
        ("ExportUnique", "Уникальных: {0}", "Unique: {0}"),
        ("ExportDupYes", "ПОВТОРЫ ЕСТЬ: {0}", "DUPLICATES: {0}"),
        ("ExportDupNo", "ПОВТОРОВ НЕТ — все теги уникальные.", "NO DUPLICATES — all tags are unique."),
    ];
}
