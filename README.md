# Chinese Character Learning Cards Generator

A Python tool for generating printable Chinese character learning cards with automatic pinyin and English translation generation. Creates 3×3 grid layouts in PPTX or PDF format for easy printing and studying.

## Features

- **Input**: CSV/TSV files with Chinese words (supports missing pinyin/translations)
- **Auto-generation**: Automatic pinyin generation using `pypinyin` and English translations using built-in dictionary
- **Output formats**: 
  - **PPTX**: Editable PowerPoint slides with independent text boxes
  - **PDF**: Print-ready PDF with vector graphics
- **Customizable layout**: Adjustable card size, spacing, margins, and fonts
- **Offline operation**: No internet required, uses built-in Chinese-English dictionary

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python src/gen_cards.py --help
   ```

## Quick Start

### Option 1: Web UI (Recommended) 🌟

1. **Launch the web interface**:
   ```bash
   python -m streamlit run web_ui.py
   ```

2. **Open your browser** to `http://localhost:8501`

3. **Enter Chinese characters** in the text box (space-separated):
   ```
   爱 家 朋友 水 火 山 月 日 木
   ```

   Or enter continuous text and use auto-segmentation:
   ```
   我爱我的家人朋友们 → 我 爱 我的 家人 朋友 们
   ```

4. **See real-time preview** with 3×3 grid layout and click "导出 PPTX" or "导出 PDF"

**Web UI Features:**
- 🎯 **Real-time preview**: See your cards as you type
- ⚙️ **Interactive controls**: Adjust fonts, sizes, and layout with sliders
- 📱 **Responsive design**: Works on desktop and mobile browsers
- 🚀 **One-click export**: Download PPTX or PDF instantly
- 🔧 **Advanced options**: Fine-tune spacing, margins, and typography
- 🔤 **Smart segmentation**: Auto-split continuous Chinese text into words
- 📊 **Usage statistics**: Track your card generation history
- 📁 **File upload**: Import CSV files with batch processing

### Option 2: Command Line

1. **Prepare your word list** (see `samples/words.csv` for format):
   ```csv
   hanzi,pinyin,english
   爱,,love
   家,jiā,home
   朋友,péngyou,friend
   水,,water
   ```

2. **Generate PPTX cards with auto-completion**:
   ```bash
   python src/gen_cards.py \
     --in samples/words.csv \
     --out out/cards.pptx \
     --format pptx \
     --auto-pinyin --auto-translate \
     --card-size 5.5 --gap 0.5
   ```

3. **Generate PDF cards**:
   ```bash
   python src/gen_cards.py \
     --in samples/words.csv \
     --out out/cards.pdf \
     --format pdf \
     --auto-pinyin --auto-translate \
     --card-size 5.5 --gap 0.5
   ```

## Usage

### Basic Command Structure
```bash
python src/gen_cards.py --in INPUT_FILE --out OUTPUT_FILE --format FORMAT [OPTIONS]
```

### Input File Format

**CSV format** (recommended):
```csv
hanzi,pinyin,english
爱,,love
家,jiā,home
朋友,péngyou,friend
```

**Flexible column names**: The tool recognizes various column names:
- Chinese: `hanzi`, `chinese`, `word`, `character`
- Pinyin: `pinyin`, `pronunciation`, `reading`
- English: `english`, `translation`, `meaning`, `definition`

**Missing data**: Leave pinyin or English columns empty to auto-generate them.

### Command Line Options

#### Required Arguments
- `--in INPUT_FILE`: Input CSV/TSV file
- `--out OUTPUT_FILE`: Output file path
- `--format {pptx,pdf}`: Output format

#### Processing Options
- `--auto-pinyin`: Auto-generate pinyin for missing entries
- `--auto-translate`: Auto-generate English translations
- `--heteronym`: Show multiple pronunciations for polyphonic characters
- `--dict DICT_PATH`: Custom dictionary file path

#### Layout Options
- `--page {A4,Letter}`: Page size (default: A4)
- `--card-size SIZE`: Card size in cm (default: 6.0)
- `--gap SIZE`: Gap between cards in cm (default: 0.6)
- `--margin SIZE`: Page margin in cm (default: 1.0)

#### Font Options
- `--font-hanzi SIZE`: Chinese character font size (default: 48)
- `--font-pinyin SIZE`: Pinyin font size (default: 18)
- `--font-english SIZE`: English font size (default: 14)

### Examples

**Basic usage with auto-generation**:
```bash
python src/gen_cards.py --in words.csv --out cards.pptx --format pptx --auto-pinyin --auto-translate
```

**Custom layout for smaller cards**:
```bash
python src/gen_cards.py --in words.csv --out cards.pdf --format pdf \
  --card-size 5 --gap 0.8 --margin 1.5 --auto-pinyin --auto-translate
```

**Large fonts for beginners**:
```bash
python src/gen_cards.py --in words.csv --out cards.pptx --format pptx \
  --font-hanzi 60 --font-pinyin 24 --font-english 18 --auto-pinyin --auto-translate
```

**Show multiple pronunciations**:
```bash
python src/gen_cards.py --in words.csv --out cards.pptx --format pptx \
  --heteronym --auto-pinyin --auto-translate
```

## Project Structure

```
hanzi-cards/
├── data/
│   └── mini_cedict.json        # Built-in Chinese-English dictionary
├── src/
│   ├── gen_cards.py            # Main CLI script
│   ├── pinyin_utils.py         # Pinyin generation utilities
│   ├── dict_utils.py           # Dictionary lookup utilities
│   ├── layout_pptx.py          # PPTX generation
│   └── layout_pdf.py           # PDF generation
├── samples/
│   └── words.csv               # Sample word list
├── out/                        # Generated output files
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Dictionary

The tool includes a built-in mini dictionary (`data/mini_cedict.json`) with ~300 common Chinese words and characters. For better coverage, you can:

1. **Use the built-in dictionary** (default): Covers most common words
2. **Add full CEDICT**: Download `cedict_ts.u8` from [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) and place it in the `data/` directory

## Output Formats

### PPTX Format
- **Advantages**: Editable in PowerPoint, independent text boxes, easy to modify
- **Use case**: When you need to edit cards after generation
- **Features**: Each card is a separate shape with independent borders

### PDF Format
- **Advantages**: Print-ready, consistent formatting, smaller file size
- **Use case**: Direct printing without editing
- **Features**: Vector graphics, professional print quality

## Tips

1. **Card Layout**: The 3×3 grid fits 9 cards per page. Larger word lists automatically create multiple pages.

2. **Font Considerations**: 
   - Chinese characters work best with fonts like SimSun, SimHei, or system Chinese fonts
   - The tool automatically tries to use appropriate fonts for Chinese text

3. **Printing**: 
   - Use PDF format for the most reliable printing results
   - A4 page size with 6cm cards and default margins fits standard printers well

4. **Customization**: 
   - Start with default settings and adjust based on your needs
   - Smaller cards (4-5cm) allow for more cards per page
   - Larger fonts help beginners but may require larger cards

## Troubleshooting

**"No translation found" warnings**: Normal for uncommon words. You can:
- Add translations manually to your CSV file
- Use the full CEDICT dictionary for better coverage

**Font issues**: If Chinese characters don't display correctly:
- Ensure you have Chinese fonts installed on your system
- Try different output formats (PPTX vs PDF)

**Layout issues**: If cards don't fit on the page:
- Reduce card size (`--card-size`)
- Reduce margins (`--margin`)
- Use Letter page size for US standard paper

## License

This project is open source. The CC-CEDICT dictionary data is licensed under Creative Commons Attribution-Share Alike 3.0.

## Contributing

Contributions welcome! Areas for improvement:
- Additional output formats (DOCX, HTML)
- More dictionary sources
- GUI interface
- Additional languages
