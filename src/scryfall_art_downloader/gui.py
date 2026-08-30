import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .downloader import download_entries
from .parser import DeckParseError, parse_deck_list, unique_printings


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Scryfall Card Art Downloader")
        self.root.geometry("780x650")
        self.events: queue.Queue = queue.Queue()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "downloads"))
        self.image_type = tk.StringVar(value="png")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)

        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Label(top, text="Deck list").pack(side="left")
        ttk.Button(top, text="Load file…", command=self.load_file).pack(side="right")

        self.deck_text = tk.Text(frame, height=18, wrap="none", undo=True)
        self.deck_text.pack(fill="both", expand=True, pady=(6, 12))
        self.deck_text.insert("1.0", "1 Book of Mazarbul (LTR) 116\n")

        output = ttk.Frame(frame)
        output.pack(fill="x", pady=4)
        ttk.Label(output, text="Output directory:").pack(side="left")
        ttk.Entry(output, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(output, text="Browse…", command=self.choose_output).pack(side="right")

        options = ttk.Frame(frame)
        options.pack(fill="x", pady=8)
        ttk.Label(options, text="Image:").pack(side="left")
        ttk.Radiobutton(options, text="Full card (PNG)", variable=self.image_type, value="png").pack(side="left", padx=8)
        ttk.Radiobutton(options, text="Artwork only", variable=self.image_type, value="art_crop").pack(side="left", padx=8)
        self.download_button = ttk.Button(options, text="Download", command=self.start_download)
        self.download_button.pack(side="right")

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 8))
        ttk.Label(frame, text="Results").pack(anchor="w")
        self.log = tk.Text(frame, height=9, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=False, pady=(4, 0))

    def load_file(self) -> None:
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            try:
                text = Path(filename).read_text(encoding="utf-8-sig")
            except OSError as exc:
                messagebox.showerror("Could not load deck", str(exc))
                return
            self.deck_text.delete("1.0", "end")
            self.deck_text.insert("1.0", text)

    def choose_output(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)

    def start_download(self) -> None:
        try:
            entries = unique_printings(parse_deck_list(self.deck_text.get("1.0", "end")))
        except DeckParseError as exc:
            messagebox.showerror("Invalid deck list", str(exc))
            return
        self.download_button.configure(state="disabled")
        self.progress.configure(maximum=len(entries), value=0)
        self._set_log("")
        thread = threading.Thread(
            target=self._worker,
            args=(entries, Path(self.output_dir.get()), self.image_type.get()),
            daemon=True,
        )
        thread.start()
        self.root.after(75, self._poll_events)

    def _worker(self, entries, output_dir, image_type) -> None:
        def progress(index, total, result):
            self.events.put(("progress", index, total, result))

        results = download_entries(entries, output_dir, image_type=image_type, progress=progress)
        self.events.put(("done", results, output_dir))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, index, _, result = event
                    self.progress.configure(value=index)
                    detail = f" — {result.message}" if result.message else ""
                    self._append_log(f"{result.status.upper()}: {result.entry.name}{detail}\n")
                elif event[0] == "done":
                    _, results, output_dir = event
                    self.download_button.configure(state="normal")
                    failed = sum(result.status == "failed" for result in results)
                    messagebox.showinfo(
                        "Download complete",
                        f"Processed {len(results)} printing(s) with {failed} failure(s).\n\n{output_dir.resolve()}",
                    )
                    return
        except queue.Empty:
            self.root.after(75, self._poll_events)

    def _set_log(self, value: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", value)
        self.log.configure(state="disabled")

    def _append_log(self, value: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", value)
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

