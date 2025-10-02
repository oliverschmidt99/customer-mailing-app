// static/js/settings.js
document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.checked =
      document.documentElement.getAttribute("data-theme") === "dark";

    themeToggle.addEventListener("change", () => {
      const newTheme = themeToggle.checked ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
    });
  }

  const settingsAppRoot = document.getElementById("settings-app");
  if (settingsAppRoot) {
    const { createApp, ref, computed, watch } = Vue;

    createApp({
      setup() {
        // --- DATEN ---
        const initialOptionsData = JSON.parse(
          document.getElementById("selection-options-data").textContent
        );
        const initialConfigData = JSON.parse(
          document.getElementById("config-data").textContent
        );

        // --- REAKTIVE STATES ---
        const options = ref(JSON.parse(JSON.stringify(initialOptionsData)));
        const saveStatus = ref("");
        const isSuccess = ref(false);

        const senderAddress = ref(initialConfigData.sender_address || "");
        const currentLogoUrl = ref(initialConfigData.logo_url || null);

        const exportSettings = ref({
          senderFontSize: initialConfigData.export_sender_font_size || 7,
          logoSize: initialConfigData.export_logo_size || 8,
          recipientFontSize: initialConfigData.export_recipient_font_size || 10,
          senderAlignment: initialConfigData.export_sender_alignment || "L",
          recipientAlignment:
            initialConfigData.export_recipient_alignment || "L",
        });
        const exportSettingsSaveStatus = ref("");
        const isExportSettingsSuccess = ref(false);

        const addressFormats = ref({
          company:
            initialConfigData.address_format_company ||
            "{firmenname}\nz. Hd. {name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}",
          private:
            initialConfigData.address_format_private ||
            "{name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}",
        });
        const addressFormatSaveStatus = ref("");
        const isAddressFormatSuccess = ref(false);

        // --- COMPUTED PROPERTIES ---
        const hasChanges = computed(
          () =>
            JSON.stringify(options.value) !== JSON.stringify(initialOptionsData)
        );

        const hasExportSettingsChanges = computed(() => {
          return (
            senderAddress.value !== (initialConfigData.sender_address || "") ||
            exportSettings.value.senderFontSize !==
              (initialConfigData.export_sender_font_size || 7) ||
            exportSettings.value.logoSize !==
              (initialConfigData.export_logo_size || 8) ||
            exportSettings.value.recipientFontSize !==
              (initialConfigData.export_recipient_font_size || 10) ||
            exportSettings.value.senderAlignment !==
              (initialConfigData.export_sender_alignment || "L") ||
            exportSettings.value.recipientAlignment !==
              (initialConfigData.export_recipient_alignment || "L")
          );
        });

        const hasAddressFormatChanges = computed(() => {
          const initialCompany =
            initialConfigData.address_format_company ||
            "{firmenname}\nz. Hd. {name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}";
          const initialPrivate =
            initialConfigData.address_format_private ||
            "{name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}";
          return (
            addressFormats.value.company !== initialCompany ||
            addressFormats.value.private !== initialPrivate
          );
        });

        const previewAddressBlock = computed(() => {
          const previewData = {
            firmenname: "Musterfirma GmbH & Co. KG",
            anrede: "z. Hd. Frau",
            titel: "Prof. Dr.",
            vorname: "Erika",
            nachname: "Mustermann",
            strasse: "Ein sehr langer Straßenname",
            hausnummer: "123a",
            plz: "12345",
            ort: "Musterstadt",
            land: "Deutschland",
          };

          const name_komplett = [
            previewData.anrede,
            previewData.titel,
            previewData.vorname,
            previewData.nachname,
          ]
            .filter(Boolean)
            .join(" ");

          const placeholders = {
            "{firmenname}": previewData.firmenname,
            "{anrede}": previewData.anrede,
            "{titel}": previewData.titel,
            "{vorname}": previewData.vorname,
            "{nachname}": previewData.nachname,
            "{name_komplett}": name_komplett,
            "{strasse}": previewData.strasse,
            "{hausnummer}": previewData.hausnummer,
            "{plz}": previewData.plz,
            "{ort}": previewData.ort,
            "{land}": previewData.land,
          };

          let template = addressFormats.value.company;
          let result = template;
          for (const key in placeholders) {
            result = result.replace(
              new RegExp(key.replace(/[{}]/g, "\\$&"), "g"),
              placeholders[key]
            );
          }

          return result
            .split("\n")
            .filter((line) => line.trim() !== "")
            .join("<br>");
        });

        // --- METHODEN ---
        const addOption = () => options.value.push({ name: "", values: "" });
        const removeOption = (index) => options.value.splice(index, 1);

        const saveOptions = async () => {
          saveStatus.value = "Speichert...";
          isSuccess.value = false;
          try {
            const response = await fetch("/settings/api/selection-options", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ options: options.value }),
            });
            const result = await response.json();
            if (result.success) {
              saveStatus.value = result.message;
              isSuccess.value = true;
              Object.assign(
                initialOptionsData,
                JSON.parse(JSON.stringify(options.value))
              );
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            saveStatus.value = `Fehler: ${error.message}`;
            isSuccess.value = false;
          }
        };

        const handleLogoUpload = async (event) => {
          const file = event.target.files[0];
          if (!file) return;
          const formData = new FormData();
          formData.append("logo", file);
          exportSettingsSaveStatus.value = "Logo wird hochgeladen...";
          isExportSettingsSuccess.value = false;
          try {
            const response = await fetch("/settings/api/upload-logo", {
              method: "POST",
              body: formData,
            });
            const result = await response.json();
            if (result.success) {
              exportSettingsSaveStatus.value = result.message;
              isExportSettingsSuccess.value = true;
              currentLogoUrl.value = result.logo_url;
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            exportSettingsSaveStatus.value = `Fehler beim Upload: ${error.message}`;
            isExportSettingsSuccess.value = false;
          }
        };

        const saveExportSettings = async () => {
          exportSettingsSaveStatus.value = "Speichert...";
          isExportSettingsSuccess.value = false;
          const payload = {
            sender_address: senderAddress.value,
            export_sender_font_size: exportSettings.value.senderFontSize,
            export_logo_size: exportSettings.value.logoSize,
            export_recipient_font_size: exportSettings.value.recipientFontSize,
            export_sender_alignment: exportSettings.value.senderAlignment,
            export_recipient_alignment: exportSettings.value.recipientAlignment,
          };
          try {
            const response = await fetch("/settings/api/config", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (result.success) {
              exportSettingsSaveStatus.value = result.message;
              isExportSettingsSuccess.value = true;
              initialConfigData.sender_address = senderAddress.value;
              initialConfigData.export_sender_font_size =
                exportSettings.value.senderFontSize;
              initialConfigData.export_logo_size =
                exportSettings.value.logoSize;
              initialConfigData.export_recipient_font_size =
                exportSettings.value.recipientFontSize;
              initialConfigData.export_sender_alignment =
                exportSettings.value.senderAlignment;
              initialConfigData.export_recipient_alignment =
                exportSettings.value.recipientAlignment;
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            exportSettingsSaveStatus.value = `Fehler: ${error.message}`;
            isExportSettingsSuccess.value = false;
          }
        };

        const saveAddressFormats = async () => {
          addressFormatSaveStatus.value = "Speichert...";
          isAddressFormatSuccess.value = false;
          const payload = {
            address_format_company: addressFormats.value.company,
            address_format_private: addressFormats.value.private,
          };
          try {
            const response = await fetch("/settings/api/config", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (result.success) {
              addressFormatSaveStatus.value = result.message;
              isAddressFormatSuccess.value = true;
              initialConfigData.address_format_company =
                addressFormats.value.company;
              initialConfigData.address_format_private =
                addressFormats.value.private;
            } else {
              throw new Error(result.error);
            }
          } catch (error) {
            addressFormatSaveStatus.value = `Fehler: ${error.message}`;
            isAddressFormatSuccess.value = false;
          }
        };

        // --- WATCHERS ---
        watch(
          saveStatus,
          (v) => v && setTimeout(() => (saveStatus.value = ""), 3000)
        );
        watch(
          exportSettingsSaveStatus,
          (v) =>
            v && setTimeout(() => (exportSettingsSaveStatus.value = ""), 3000)
        );
        watch(
          addressFormatSaveStatus,
          (v) =>
            v && setTimeout(() => (addressFormatSaveStatus.value = ""), 3000)
        );

        return {
          options,
          hasChanges,
          saveStatus,
          isSuccess,
          addOption,
          removeOption,
          saveOptions,
          senderAddress,
          currentLogoUrl,
          handleLogoUpload,
          exportSettings,
          hasExportSettingsChanges,
          saveExportSettings,
          exportSettingsSaveStatus,
          isExportSettingsSuccess,
          addressFormats,
          hasAddressFormatChanges,
          saveAddressFormats,
          addressFormatSaveStatus,
          isAddressFormatSuccess,
          previewAddressBlock,
        };
      },
      delimiters: ["{[", "]}"],
    }).mount(settingsAppRoot);
  }
});
