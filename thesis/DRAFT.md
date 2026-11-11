# Текст диплома

Текущая версия (армянский): `DIPLOMA.docx`. Источник — `hy/*.md` (по одному файлу на главу), сборка:

```sh
python -m pip install -e '.[thesis]'
python scripts/thesis_figures_hy.py   # армянские рисунки в reports/thesis/
python scripts/build_thesis_hy.py     # thesis/DIPLOMA.docx
```

После открытия в Word обновите оглавление (Word предложит обновить поля; иначе ПКМ по оглавлению → Обновить поле). Поля титульного листа (университет, кафедра, специальность, руководитель) заполняются вручную или в `TITLE` в `scripts/build_thesis_hy.py`.

Числа в главе 5 взяты из `reports/*.json`, `reports/thesis/video_results.json` и `reports/counting-thesis-v1-v8s.json`.

Архив: `archive/DIPLOMA-ru-2026-10-10.docx` — русский черновик от 10 октября (источник `CHAPTERS.md`, `scripts/build_thesis.py`).

Материалы выступления: `DEFENSE_NOTES.md`; презентация: `presentation/DEFENSE.pptx` (ещё не обновлена).
