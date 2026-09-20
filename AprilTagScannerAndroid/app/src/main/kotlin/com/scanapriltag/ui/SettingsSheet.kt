package com.scanapriltag.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.VolumeUp
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.scanapriltag.ScannerUiState
import com.scanapriltag.localization.AppLanguage
import com.scanapriltag.localization.L
import com.scanapriltag.services.SpeedPreset
import com.scanapriltag.services.SpeedPresetSettings
import com.scanapriltag.services.TagFamilyCatalog
import com.scanapriltag.ui.theme.SectionHeadingStyle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsBottomSheet(
    state: ScannerUiState,
    onDismiss: () -> Unit,
    onLanguageChange: (AppLanguage) -> Unit,
    onFamilyChange: (String) -> Unit,
    onMultiFamilyChange: (Boolean) -> Unit,
    onPresetChange: (SpeedPreset) -> Unit,
    onBeepChange: (Boolean) -> Unit,
    onMissChange: (Int) -> Unit,
    onReconnect: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = MaterialTheme.colorScheme.surface,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = L.settingsGroup,
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(bottom = 4.dp),
            )

            SettingsSection(
                title = L.s("SectionApp"),
                icon = Icons.Outlined.Language,
            ) {
                LanguageSelector(
                    selected = state.language,
                    onSelected = onLanguageChange,
                )
            }

            SettingsSection(
                title = L.s("SectionDetection"),
                icon = Icons.Outlined.QrCodeScanner,
            ) {
                SettingDropdown(
                    label = L.familyAuto,
                    options = TagFamilyCatalog.allFamilies,
                    selected = state.selectedFamily,
                    enabled = state.settingsEnabled,
                    itemLabel = TagFamilyCatalog::getLabel,
                    onSelected = onFamilyChange,
                )
                ListItem(
                    headlineContent = { Text(L.multiFamily, style = MaterialTheme.typography.bodyMedium) },
                    trailingContent = {
                        Switch(
                            checked = state.multiFamily,
                            onCheckedChange = onMultiFamilyChange,
                            enabled = state.settingsEnabled,
                        )
                    },
                    colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surface),
                )
                SettingDropdown(
                    label = L.speed,
                    options = SpeedPreset.entries.toList(),
                    selected = state.preset,
                    enabled = state.settingsEnabled,
                    itemLabel = SpeedPresetSettings::label,
                    onSelected = onPresetChange,
                )
                SettingDropdown(
                    label = L.miss,
                    options = buildList {
                        addAll(listOf(4, 6, 8, 12, 16, 24))
                        if (state.missLimit !in this) add(state.missLimit)
                    }.sorted(),
                    selected = state.missLimit,
                    enabled = state.settingsEnabled,
                    itemLabel = { it.toString() },
                    onSelected = onMissChange,
                )
            }

            SettingsSection(
                title = L.s("SectionCamera"),
                icon = Icons.Outlined.CameraAlt,
            ) {
                OutlinedButton(
                    onClick = {
                        onReconnect()
                        onDismiss()
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .defaultMinSize(minHeight = 48.dp),
                    enabled = state.settingsEnabled,
                ) {
                    Icon(Icons.Outlined.Refresh, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(L.reconnectCamera)
                }
            }

            SettingsSection(
                title = L.s("SectionFeedback"),
                icon = Icons.Outlined.VolumeUp,
            ) {
                ListItem(
                    headlineContent = { Text(L.beepOnDuplicate, style = MaterialTheme.typography.bodyMedium) },
                    trailingContent = {
                        Switch(
                            checked = state.beepOnDuplicate,
                            onCheckedChange = onBeepChange,
                            enabled = state.settingsEnabled,
                        )
                    },
                    colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surface),
                )
            }
        }
    }
}

@Composable
private fun LanguageSelector(
    selected: AppLanguage,
    onSelected: (AppLanguage) -> Unit,
) {
    Text(
        text = L.languageLabel,
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(bottom = 6.dp),
    )
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        AppLanguage.entries.forEach { language ->
            val isSelected = language == selected
            OutlinedButton(
                onClick = { onSelected(language) },
                modifier = Modifier
                    .weight(1f)
                    .defaultMinSize(minHeight = 48.dp),
                enabled = !isSelected,
                colors = ButtonDefaults.outlinedButtonColors(
                    containerColor = if (isSelected) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        MaterialTheme.colorScheme.surface
                    },
                    contentColor = MaterialTheme.colorScheme.onSurface,
                ),
                border = BorderStroke(
                    width = if (isSelected) 2.dp else 1.dp,
                    color = if (isSelected) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.outline
                    },
                ),
            ) {
                Text(
                    text = L.languageName(language),
                    fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                )
            }
        }
    }
}

@Composable
fun SettingsSection(
    title: String,
    icon: ImageVector,
    content: @Composable ColumnScope.() -> Unit,
) {
    Spacer(modifier = Modifier.height(8.dp))
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(bottom = 4.dp),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(18.dp),
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = title.uppercase(),
            style = SectionHeadingStyle,
            color = MaterialTheme.colorScheme.primary,
        )
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    Spacer(modifier = Modifier.height(4.dp))
    Column(
        verticalArrangement = Arrangement.spacedBy(4.dp),
        content = content,
    )
    Spacer(modifier = Modifier.height(4.dp))
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun <T> SettingDropdown(
    label: String,
    options: List<T>,
    selected: T,
    enabled: Boolean,
    itemLabel: (T) -> String,
    onSelected: (T) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { if (enabled) expanded = it },
        modifier = Modifier.fillMaxWidth(),
    ) {
        OutlinedTextField(
            value = itemLabel(selected),
            onValueChange = {},
            readOnly = true,
            enabled = enabled,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier
                .menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled)
                .fillMaxWidth(),
            colors = ExposedDropdownMenuDefaults.outlinedTextFieldColors(),
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(itemLabel(option)) },
                    onClick = {
                        expanded = false
                        if (option != selected) {
                            onSelected(option)
                        }
                    },
                )
            }
        }
    }
}
