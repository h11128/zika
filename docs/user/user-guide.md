# Chinese Flashcard Application - User Guide

Welcome to the Chinese Flashcard Application! This guide will help you create, customize, and export beautiful Chinese language flashcards.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Flashcards](#creating-flashcards)
3. [Customizing Layout](#customizing-layout)
4. [Typography and Styling](#typography-and-styling)
5. [Exporting Flashcards](#exporting-flashcards)
6. [Tips and Best Practices](#tips-and-best-practices)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### System Requirements

- Python 3.8 or higher
- Web browser (Chrome, Firefox, Safari, or Edge)
- 2GB RAM minimum
- 100MB free disk space

### Installation

1. **Download the application** from the releases page
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   streamlit run app.py
   ```
4. **Open your browser** to `http://localhost:8501`

### First Launch

When you first open the application, you'll see:
- A text input area for entering Chinese text
- Layout controls on the sidebar
- A preview area showing your flashcards
- Export options at the bottom

## Creating Flashcards

### Input Methods

#### Method 1: Direct Text Input
1. Type or paste Chinese text in the main input area
2. Separate words/phrases with spaces or new lines
3. The application will automatically segment the text
4. Click "Generate Cards" to create flashcards

**Example:**
```
你好 世界 学习 中文
```

#### Method 2: CSV Upload
1. Click "Upload CSV" in the sidebar
2. Select a CSV file with columns: `hanzi`, `pinyin`, `english`
3. The application will import all rows as flashcards

**CSV Format:**
```csv
hanzi,pinyin,english
你好,nǐ hǎo,hello
世界,shì jiè,world
学习,xué xí,study
```

#### Method 3: Manual Entry
1. Use the "Add Card" button to create individual cards
2. Fill in the Chinese characters (required)
3. Optionally add pinyin and English translations
4. Click "Save Card" to add to your collection

### Automatic Features

- **Pinyin Generation**: Automatically generates pinyin for Chinese characters
- **Text Segmentation**: Intelligently separates Chinese text into words
- **Duplicate Detection**: Prevents duplicate cards from being created
- **Auto-save**: Your work is automatically saved as you type

## Customizing Layout

### Page Layout

#### Grid Configuration
- **Rows**: Number of card rows per page (1-10)
- **Columns**: Number of card columns per page (1-10)
- **Cards per page**: Automatically calculated (rows × columns)

#### Page Settings
- **Page Size**: A4, Letter, Legal, A3, A5
- **Orientation**: Portrait or Landscape
- **Margins**: Adjustable margins in centimeters
- **Card Spacing**: Gap between cards

#### Auto-sizing
- Enable "Auto-size cards" for optimal card dimensions
- Cards automatically resize to fit the page layout
- Manual override available for custom sizes

### Navigation

- **Page Navigation**: Use arrow buttons or page numbers
- **Cards per Page**: Adjust layout to show more/fewer cards
- **Preview Mode**: Toggle between edit and preview modes

### Layout Presets

Choose from predefined layouts:
- **Study Cards** (2×3): Perfect for detailed study
- **Quick Review** (3×4): Compact for rapid review
- **Presentation** (2×2): Large cards for teaching
- **Pocket Cards** (4×5): Small cards for printing

## Typography and Styling

### Font Settings

#### Chinese Characters (Hanzi)
- **Font Size**: 12-72 points
- **Font Family**: SimSun, Microsoft YaHei, NSimSun
- **Weight**: Normal, Bold
- **Color**: Any hex color code

#### Pinyin
- **Font Size**: 8-36 points
- **Font Family**: Arial, Times New Roman, Calibri
- **Style**: Normal, Italic
- **Position**: Above or below hanzi

#### English Translation
- **Font Size**: 8-24 points
- **Font Family**: Arial, Times New Roman, Calibri
- **Position**: Bottom of card
- **Visibility**: Show/hide toggle

### Visual Styling

#### Colors
- **Background**: Card background color
- **Text**: Primary text color
- **Accent**: Border and highlight color
- **Theme**: Light, Dark, or Custom

#### Card Appearance
- **Border**: Width and style options
- **Corners**: Rounded or square corners
- **Shadow**: Drop shadow effects
- **Padding**: Internal spacing

#### Themes
- **Classic**: Traditional black on white
- **Modern**: Clean, minimalist design
- **High Contrast**: Accessibility-focused
- **Custom**: Create your own theme

## Exporting Flashcards

### Export Formats

#### PDF Export
- **Quality**: High-resolution for printing
- **Size**: Matches your layout settings
- **Features**: Searchable text, bookmarks
- **Use Cases**: Printing, digital study

#### PowerPoint Export
- **Format**: .pptx compatible with all versions
- **Layout**: One card per slide or multiple cards
- **Features**: Editable text, animations
- **Use Cases**: Presentations, interactive study

#### Image Export
- **Formats**: PNG, JPEG
- **Resolution**: 300 DPI for print quality
- **Batch**: Export all cards as individual images
- **Use Cases**: Social media, mobile apps

### Export Options

#### Page Settings
- **Include Page Numbers**: Add page numbers to exports
- **Header/Footer**: Custom text on each page
- **Watermark**: Add your name or logo

#### Content Options
- **Show Pinyin**: Include/exclude pinyin
- **Show English**: Include/exclude translations
- **Card Numbers**: Add sequential numbers
- **QR Codes**: Link to audio pronunciation

#### Quality Settings
- **Resolution**: 150-600 DPI
- **Compression**: Balance file size and quality
- **Color Space**: RGB or CMYK for printing

### Batch Operations

- **Export All**: Export your entire collection
- **Export Selection**: Choose specific cards
- **Export by Tag**: Filter by categories
- **Export Range**: Select page ranges

## Tips and Best Practices

### Creating Effective Flashcards

1. **Keep it Simple**: One concept per card
2. **Use Context**: Include example sentences
3. **Add Audio**: Use QR codes for pronunciation
4. **Regular Review**: Export for spaced repetition
5. **Organize**: Use tags and categories

### Layout Optimization

1. **Print Testing**: Test print layouts before bulk printing
2. **Screen vs Print**: Different settings for digital vs physical use
3. **Accessibility**: Ensure sufficient contrast and font size
4. **Consistency**: Use the same layout for card sets

### Performance Tips

1. **Batch Operations**: Process multiple cards together
2. **Cache Management**: Clear cache if experiencing slowdowns
3. **File Size**: Balance quality with file size for exports
4. **Browser**: Use Chrome or Firefox for best performance

### Study Strategies

1. **Progressive Disclosure**: Start with hanzi only, reveal pinyin/English
2. **Mixed Practice**: Combine recognition and production
3. **Spaced Repetition**: Review cards at increasing intervals
4. **Active Recall**: Test yourself before checking answers

## Troubleshooting

### Common Issues

#### Application Won't Start
- **Check Python Version**: Ensure Python 3.8+
- **Install Dependencies**: Run `pip install -r requirements.txt`
- **Port Conflicts**: Try a different port with `--server.port 8502`

#### Cards Not Displaying
- **Clear Cache**: Refresh the browser page
- **Check Input**: Ensure Chinese text is properly formatted
- **Browser Compatibility**: Try a different browser

#### Export Problems
- **File Permissions**: Check write permissions in export directory
- **Disk Space**: Ensure sufficient free space
- **Large Files**: Reduce quality settings for large exports

#### Performance Issues
- **Memory**: Close other applications to free RAM
- **Cache**: Clear browser cache and application cache
- **Card Count**: Process smaller batches for large collections

### Error Messages

#### "Invalid Chinese Text"
- **Cause**: Text doesn't contain recognizable Chinese characters
- **Solution**: Check input encoding and character validity

#### "Export Failed"
- **Cause**: Insufficient permissions or disk space
- **Solution**: Check file permissions and available storage

#### "Layout Error"
- **Cause**: Invalid layout parameters
- **Solution**: Reset layout to default settings

### Getting Help

1. **Documentation**: Check this guide and API docs
2. **Examples**: Review sample files and templates
3. **Community**: Join our user forum for tips and tricks
4. **Support**: Contact support for technical issues

### Keyboard Shortcuts

- **Ctrl+N**: New card
- **Ctrl+S**: Save current work
- **Ctrl+E**: Export current view
- **Ctrl+P**: Print preview
- **Ctrl+Z**: Undo last action
- **Ctrl+Y**: Redo last action
- **F5**: Refresh preview
- **Esc**: Cancel current operation

### Accessibility Features

- **High Contrast Mode**: For users with visual impairments
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: Compatible with screen readers
- **Font Scaling**: Adjustable font sizes
- **Color Blind Support**: Alternative color schemes

## Advanced Features

### Custom CSS
Add custom styling with CSS:
```css
.card {
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Automation
Automate repetitive tasks:
- Batch import from multiple files
- Scheduled exports
- Template-based card generation

### Integration
Connect with other tools:
- Anki deck export
- Quizlet import/export
- Google Sheets integration

Remember: The best flashcards are the ones you'll actually use. Start simple and gradually customize as you become more familiar with the application!
