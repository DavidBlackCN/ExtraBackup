# ExtraBackup

> **ExtraBackup — Give your backups a warm (or multiple) home.**  
> A distributed backup plugin for **MCDR** that automatically uploads PrimeBackup backups to local disks, NAS, and (in the future) cloud storage (e.g., Baidu Netdisk). Keep your world safe from sudden disk failures. :)

> **Note:** ExtraBackup requires **PrimeBackup**. Huge thanks to Fallen — without that groundwork, this plugin wouldn’t exist.

The current version supports **local-disk backup only**. FTP and other storage modes are under active development.

---

## 📦 What It Does

- Automatically exports and uploads PrimeBackup backups
- Distributed storage (use multiple backup locations)
- Skips duplicate files automatically
- Download, delete, prune, and language switch built in
- Scheduled tasks for upload & prune (time-interval based)

---

## 🧭 Commands

### `!!exb`
Show plugin status and command help.

---

### `!!exb upload [id]`
Upload a specific backup to enabled paths in backup_path.json (without persistent files in pb_files/export).  
- `id` supports PrimeBackup special IDs like `latest`, `~3`, etc.  
- If `id` is omitted, it defaults to `latest`.
- Uploaded file name format: `backup-YYYY_MM_DD_N.tar` (`N` is the upload sequence of the day).

---

### `!!exb download <file_name> [from]`
Download a file from a specified backup path back to the server.  
- `file_name`: the backup file name  
- `from`: the name of the backup path (optional; if omitted, a random available path is used)

---

### `!!exb list [location]`
List files in enabled paths configured by `backup_path.json`, with indexes.  
- If `location` is omitted → lists files across all enabled backup paths.
- If `location` is provided → lists files only in that path.

---

### `!!exb prune`
Remove outdated backup files.  
- The expiration window is configured in the config file.

---

### `!!exb delete <id>`
Delete a backup file by the index shown in `!!exb list`.

---

### `!!exb lang <language>`
Switch the plugin language.  
Supported:
- `zh_cn` (Chinese)
- `en_us` (English)

---

## ⚙️ Configuration

### Main Config — `config.json`

```jsonc
{
  "enable": "false",            // Enable this plugin
  "language": "zh_cn",          // Default language
  "max_thread": "-1",           // Max threads for upload/download (-1 = unlimited)

  "schedule_backup": {
    "enable": "false",          // Enable scheduled uploads
    "interval": "30m"           // Upload interval
  },

  "schedule_prune": {
    "enable": "false",          // Enable scheduled pruning
    "interval": "1d",           // Pruning interval
    "max_lifetime": "3d",       // Max file lifetime before considered outdated

    "prune_downloads": "true"   // Prune the exb_downloads folder
  }
}
```

---

## 📁 Backup Paths — `backup_path.json`

```jsonc
{
  "Name1": {                           // Backup path name (Chinese allowed)
    "enable": "false",                 // Enable this path
    "mode": "ftp",                     // Mode: "local" (local path) or "ftp" (remote FTP)
    "address": "ftp://example.com/folder", // local: local path; ftp: server address
    "username": "username",            // FTP username; leave empty for local (keep quotes)
    "password": "123456"               // FTP password; leave empty for local (keep quotes)
  },

  "Name2": {
    "enable": "true",
    "mode": "local",
    "address": "/folder/example",      // Local directory
    "username": "",                    // Must be empty but quoted in local mode
    "password": ""                     // Must be empty but quoted in local mode
  }
}
// Add more backup paths as needed
```
