# File Attachment Feature - Documentation

## Overview

The quotation generator now supports attaching supporting documents directly to quotations. Users can upload PDF, JPEG, JPG, PNG, DOC, DOCX, XLS, and XLSX files up to 10MB each.

## Features

✅ **Supported File Types:**
- PDF (`.pdf`)
- Images: JPEG (`.jpeg`, `.jpg`), PNG (`.png`)
- Documents: DOC (`.doc`), DOCX (`.docx`), XLS (`.xls`), XLSX (`.xlsx`)

✅ **File Size Limit:** 10MB per file

✅ **Multiple Attachments:** Users can attach multiple files in a single quotation

✅ **Easy Management:**
- View attached files with size information
- Remove unwanted attachments before generating the quotation
- Download attached files after quotation is generated

✅ **PDF Integration:**
- Attached files are referenced in the generated PDF quotation
- Shows file names and sizes in the PDF

✅ **Session Persistence:**
- Attachments are stored in Streamlit session state
- Attachments remain available during the quotation session
- Can be downloaded along with the quotation

## User Guide

### How to Attach Files

1. **Navigate to Quotation Generator**
   - Go to the "Quotation Generator" tab
   - Fill in customer and bundle details as usual

2. **Add Attachments (Optional Section)**
   - Scroll to the "Attachments (Optional)" section
   - Click the file uploader to select a file from your computer
   - Supported formats: PDF, JPEG, JPG, PNG, DOC, DOCX, XLS, XLSX
   - Maximum file size: 10MB

3. **File Validation**
   - The system validates file type and size automatically
   - ✅ Green checkmark indicates the file was accepted
   - ❌ Red error message indicates why a file was rejected

4. **Manage Attachments**
   - View all attached files with their sizes below the uploader
   - Click "Remove" button to delete any file before generating the quotation
   - Add additional files by uploading again

5. **Generate Quotation**
   - Once attachments are ready, proceed to generate the quotation
   - Click "Generate Quotation" button
   - Attachments are included in the quotation summary

6. **Download Attached Files**
   - After quotation is generated, a new "📎 Attached Documents" section appears
   - Download buttons allow downloading any attached file
   - Each button shows the original file name

## Technical Details

### File Upload Flow

```
User uploads file
    ↓
Validate file type and size
    ↓
Store in Streamlit session state (st.session_state.attachments)
    ↓
Display in UI with Remove button
    ↓
Include in quotation when generated
    ↓
Make available for download
```

### File Storage

- Files are stored in `st.session_state.attachments` dictionary
- Each file has a unique UUID identifier
- Storage includes:
  - Original file name
  - File bytes (binary data)
  - File size in MB

### Code Changes

#### app.py Modifications
- Added `uuid` and `io` imports for file handling
- Created `validate_attachment()` function to check file type and size
- Created `save_attachment()` function to store files in session state
- Added file upload UI in the Attachments section
- Added download buttons for attached files after quotation generation
- Pass attachments list to `QuoteRequest`

#### quotation_engine.py Modifications
- Added `attachments: List[Dict]` field to `QuoteRequest` dataclass
- Added `attachments` to quotation summary dictionary
- Modified `build_quote_pdf()` to display attachment list in PDF

### Constants

```python
ALLOWED_EXTENSIONS = {'.pdf', '.jpeg', '.jpg', '.png', '.doc', '.xls', '.docx', '.xlsx'}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
```

## Error Handling

### File Type Not Allowed
**Error:** "❌ File type '.ext' not allowed. Supported: PDF, JPEG, JPG, PNG, DOC, DOCX, XLS, XLSX"
**Solution:** Upload a file with one of the supported extensions

### File Size Exceeds Limit
**Error:** "❌ File size 15.25MB exceeds 10MB limit"
**Solution:** Compress the file or use a smaller file

### Session Timeout
**Note:** Attachments are stored in session state and will be cleared when:
- The browser tab is closed
- The Streamlit app is restarted
- The session expires (typically 1 hour of inactivity)

## Examples

### Example 1: Technical Specifications
1. Generate a quotation for an OPAL 15 bundle
2. Upload technical specification PDF (5MB)
3. Generate quotation - PDF includes reference to attachment
4. Customer can download both quotation PDF and technical specs

### Example 2: Multiple Documents
1. Upload product datasheet (.pdf)
2. Upload installation manual (.docx)
3. Upload warranty document (.pdf)
4. Generate quotation with all attachments referenced
5. Customer receives quotation with all supporting docs

### Example 3: Design Documents
1. Upload product design image (.jpg)
2. Upload 3D rendering (.pdf)
3. Upload floor plan (.png)
4. Generate quotation with visual references
5. Download all materials for review

## Best Practices

✅ **DO:**
- Keep file names clear and descriptive
- Use standard file formats (PDF for documents, JPG for images)
- Compress large files before uploading
- Remove unnecessary attachments to keep quotation package clean
- Test file download before sending to customers

❌ **DON'T:**
- Upload oversized files (> 10MB)
- Upload unsupported file types
- Include sensitive information in attachment file names
- Store confidential data in attachments

## Limitations

1. **File Size Limit:** Maximum 10MB per file
2. **Session-Based Storage:** Files are lost if session ends
3. **No Database Persistence:** Attachments not saved to database (can be enhanced)
4. **Single File at a Time:** File uploader accepts one file at a time
5. **No Virus Scanning:** Basic file type validation only

## Future Enhancements

Possible future improvements:
- [ ] Increase file size limit to 50MB
- [ ] Support additional file types (video, spreadsheet templates)
- [ ] Persist attachments to database/cloud storage
- [ ] Multi-file uploader widget
- [ ] Virus/malware scanning
- [ ] Attachment versioning
- [ ] Email attachments with quotation
- [ ] Attachment preview in browser

## Troubleshooting

### Files not appearing after upload
- Check browser console for errors
- Refresh the page
- Verify file size is under 10MB
- Try a different file format

### Download button not working
- Check if file still exists in session state
- Browser may have download restrictions
- Check browser download settings
- Try right-click → Save As

### Session expired
- Re-upload the files
- Consider saving important documents locally first
- Increase browser timeout settings

## Support

For issues or feature requests:
1. Check this documentation
2. Review the troubleshooting section
3. Check application logs
4. Contact the development team

---

**Version:** 1.0
**Last Updated:** May 7, 2026
**Feature Status:** ✅ Live
