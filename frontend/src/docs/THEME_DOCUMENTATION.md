# Dokumentasi Implementasi Dark/Light Mode

Dokumen ini menjelaskan bagaimana fitur Dark/Light mode diimplementasikan pada aplikasi ini, termasuk palet warna yang digunakan. Anda dapat menggunakan panduan ini untuk mereplikasi fitur serupa di aplikasi lain.

## 1. Stack Teknologi

*   **Framework**: React (Vite)
*   **Styling**: Tailwind CSS (v4)
*   **State Management**: React Context API
*   **Persistence**: `localStorage`

## 2. Mekanisme Kerja

Aplikasi menggunakan strategi **class-based** untuk mengganti tema.
1.  **State**: Sebuah state `theme` ('light' | 'dark') disimpan di React Context.
2.  **DOM Manipulation**: Saat state berubah, class `dark` ditambahkan atau dihapus dari elemen `<html>` (`document.documentElement`).
3.  **Styling**: Tailwind CSS menggunakan `dark:` modifier untuk menerapkan style spesifik saat class `dark` ada pada elemen root.

### Kode Implementasi Utama

#### A. ThemeContext (`src/context/ThemeContext.tsx`)

File ini mengatur logika perpindahan tema dan penyimpanannya di `localStorage`.

```tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Theme = 'light' | 'dark';

// ... interface definitions ...

export function ThemeProvider({ children }: { children: ReactNode }) {
    // 1. Inisialisasi state dari localStorage (default: 'dark')
    const [theme, setTheme] = useState<Theme>(() => {
        const saved = localStorage.getItem('theme');
        return (saved as Theme) || 'dark';
    });

    // 2. Efek samping untuk update DOM dan localStorage
    useEffect(() => {
        localStorage.setItem('theme', theme);
        // Menambahkan class 'dark' ke tag <html> jika theme adalah dark
        document.documentElement.classList.toggle('dark', theme === 'dark');
        document.documentElement.classList.toggle('light', theme === 'light');
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => prev === 'light' ? 'dark' : 'light');
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

// Custom hook untuk menggunakan tema di komponen lain
export function useTheme() {
    return useContext(ThemeContext);
}
```

#### B. Global Styles (`src/index.css`)

Konfigurasi CSS variable dan style dasar.

```css
@import "tailwindcss";
@variant dark (&:where(.dark, .dark *));

@theme {
  /* Warna Custom yang Konsisten */
  --color-primary: #3b82f6; /* Blue 500 */
  --color-surface: #1e293b; /* Slate 800 */
  --color-border: #334155;  /* Slate 700 */
}

body {
  /* Default (Light) vs Dark Mode */
  /* Light: bg-white text-slate-900 */
  /* Dark: bg-slate-900 text-slate-100 */
  @apply bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100;
}
```

## 3. Palet Warna (Tone Colors)

Aplikasi ini menggunakan palet warna **Slate** dari Tailwind CSS sebagai warna dasar (monokromatik) dan **Blue** sebagai warna utama (aksen).

### Slate (Warna Dasar UI)

Digunakan untuk background, border, dan teks.

| Nama Tailwind | Hex Code | Penggunaan Utama (Dark Mode) | Penggunaan Utama (Light Mode) |
| :--- | :--- | :--- | :--- |
| **Slate 50** | `#f8fafc` | - | Background alternatif |
| **Slate 100** | `#f1f5f9` | Teks Utama (Judul) | Background panel / Dropdown |
| **Slate 200** | `#e2e8f0` | - | Border |
| **Slate 300** | `#cbd5e1` | Teks Deskripsi / Subtitle | - |
| **Slate 400** | `#94a3b8` | Teks Label / Icon non-aktif | Teks Label |
| **Slate 500** | `#64748b` | Scrollbar Hover | Scrollbar Hover |
| **Slate 600** | `#475569` | Scrollbar Default | Teks Sekunder |
| **Slate 700** | `#334155` | **Border Panel / Input** | Scrollbar Default |
| **Slate 800** | `#1e293b` | **Background Panel / Input / Dropdown** | - |
| **Slate 900** | `#0f172a` | **Background Utama Aplikasi** | Teks Utama |

### Blue (Warna Aksen/Primary)

Digunakan untuk tombol primary, link, focus rings, dan state aktif.

| Nama Tailwind | Hex Code | Penggunaan |
| :--- | :--- | :--- |
| **Blue 500** | `#3b82f6` | Tombol Utama, Border Focus, Link Aktif |
| **Blue 400** | `#60a5fa` | Teks Link, add-button |

### Contoh Penerapan pada Komponen

Berikut adalah pola warna yang sering digunakan dalam komponen (diambil dari `index.css`):

**1. Input Field**
*   **Light**: Background `white`, Border `slate-200`, Text `slate-900`
*   **Dark**: Background `slate-800` (`#1e293b`), Border `slate-700` (`#334155`), Text `slate-100`

**2. Dropdown / Label Panel**
*   **Light**: Background `slate-100`, Text `slate-600`
*   **Dark**: Background `slate-800`, Text `slate-400`
*   **Border Bawah**: `slate-200` (Light) / `slate-700` (Dark)

**3. Scrollbar Custom**
*   **Thumb**: `slate-400` (Light) / `slate-700` (Dark)
*   **Hover**: `slate-500` (Light) / `slate-600` (Dark)

## 4. Cara Implementasi di Aplikasi Baru

1.  **Install Tailwind CSS**.
2.  **Copy file `ThemeContext.tsx`** ke project baru Anda.
3.  **Wrap aplikasi** dengan `ThemeProvider` di `main.tsx` atau `App.tsx`.
    ```tsx
    <ThemeProvider>
      <App />
    </ThemeProvider>
    ```
4.  **Gunakan Hook** untuk tombol toggle theme.
    ```tsx
    const { theme, toggleTheme } = useTheme();
    <button onClick={toggleTheme}>Switch to {theme === 'light' ? 'Dark' : 'Light'}</button>
    ```
5.  **Terapkan Class Tailwind**: Gunakan prefix `dark:` untuk style mode gelap.
    ```tsx
    <div className="bg-white dark:bg-slate-900 text-black dark:text-white">
      Konten Anda
    </div>
    ```
