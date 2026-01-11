# Edge Cases and Potential Issues

## 1. `generate_days()` Function

### Issues:
- **Invalid YEAR value**: If `YEAR` is set to an invalid value (e.g., negative, None, or a value that causes `datetime.date()` to raise `ValueError`), the function will crash.
- **Leap year handling**: While `datetime` handles leap years correctly, the code doesn't explicitly account for February 29th in the output formatting.

### Edge Cases:
- Empty year (not applicable, but YEAR could theoretically be invalid)
- Year 0 or negative years (would raise ValueError)

## 2. `add_page_metadata_to_days()` Function

### Issues:
- **Empty input**: If `days` list is empty, returns empty `pages` list (handled, but may cause issues downstream).
- **Partial weeks**: Last page may have fewer than 7 days (handled in HTML generation, but could be confusing).
- **Days not aligned to weeks**: Days are grouped sequentially (7 days at a time) rather than by actual calendar weeks (Monday-Sunday). This means:
  - Week boundaries may not align with actual week boundaries
  - A "week" might span two months
  - The first "week" might start mid-week

### Edge Cases:
- Empty days list → returns empty pages
- Less than 7 days total → one page with < 7 days
- Number of days not divisible by 7 → last page has fewer days

## 3. `rearrange_pages_into_signatures()` Function

### Issues:
- **Incorrect bookbinding pattern**: The current implementation uses pattern [1,2,3,4,5,6] → [1,6,2,5,3,4], but for proper bookbinding with 8-page signatures, the pattern should account for double-sided printing and folding. The actual pattern for 8 pages should be different.
- **Partial signatures**: If total pages don't divide evenly by 8, the last signature will have fewer pages, which may cause binding issues.
- **Empty pages list**: Returns empty list (handled, but may cause issues downstream).

### Edge Cases:
- Empty pages list → returns empty list
- Pages count < 8 → one signature with fewer pages (may not bind correctly)
- Pages count not divisible by 8 → last signature incomplete
- Odd number of pages in signature → rearrangement may not work correctly for binding

### Bookbinding Pattern Issue:
For 8-page signatures printed double-sided:
- Sheet 1: Pages 1 & 8 (front/back)
- Sheet 2: Pages 2 & 7 (front/back)
- Sheet 3: Pages 3 & 6 (front/back)
- Sheet 4: Pages 4 & 5 (front/back)

When folded, these should appear in order. The current pattern [1,8,2,7,3,6,4,5] might not be correct for the actual printing order needed.

## 4. `generate_html()` Function

### Issues:
- **Empty signatures**: If `signatures` is empty, generates HTML with no content (just headers).
- **Empty pages**: If a page has no days (`page.days` is empty), shows empty cells (handled, but may look odd).
- **Page with > 7 days**: Not possible with current implementation, but if it happened, would overflow the grid.
- **IndexError risk**: Accessing `day.date.month - 1` assumes valid date objects, but if a Day has an invalid date, this could crash.
- **Week numbering**: Uses `i//2 + 1` which may not correctly represent actual week numbers, especially with the rearrangement.
- **Odd number of pages**: Last spread will have only one page (handled, but may look unbalanced).

### Edge Cases:
- Empty signatures list → empty HTML
- Signature with empty pages list → skipped in iteration
- Page with 0 days → shows 7 empty cells
- Page with < 7 days → shows partial week (handled with empty cells)
- Invalid date in Day object → IndexError when accessing MONTH_NAMES
- Odd total page count → last spread has only left page

## 5. `write_html_to_file()` Function

### Issues:
- **File permissions**: No error handling for permission denied errors.
- **Invalid filename**: No validation of filename (could contain invalid characters).
- **Disk full**: No handling for disk space errors.
- **File already exists**: Will overwrite without warning.
- **Directory doesn't exist**: Will raise FileNotFoundError if directory path doesn't exist.

### Edge Cases:
- Insufficient disk space → IOError
- Permission denied → PermissionError
- Invalid filename characters → OSError
- Non-existent directory in path → FileNotFoundError
- Empty HTML string → creates empty file (handled, but may be unintended)

## 6. `main()` Function

### Issues:
- **No error handling**: If any function raises an exception, the program crashes without helpful error messages.
- **Empty results**: If `generate_days()` returns empty list, continues processing and generates empty HTML.
- **Signature grouping**: Uses hardcoded `SIGNATURE_SIZE = 8` which should match the value in `rearrange_pages_into_signatures()` (currently matches, but could diverge).

### Edge Cases:
- Any function returns None instead of empty list → AttributeError
- Empty days → empty pages → empty signatures → empty HTML
- Mismatch between SIGNATURE_SIZE in main() and rearrange function → incorrect grouping

## 7. Data Structure Issues

### Issues:
- **Day.date validation**: No validation that Day objects contain valid date objects.
- **Page.days validation**: No validation that pages contain valid Day objects.
- **Signature.pages validation**: No validation that signatures contain valid Page objects.

## 8. Week Alignment Issue (Critical)

### Major Issue:
The current implementation groups days sequentially (every 7 days) rather than by actual calendar weeks. This means:
- The first "week" might start on any day of the week (not necessarily Monday)
- Weeks may span month boundaries incorrectly
- The calendar won't align with standard weekly calendars

### Example:
If January 1, 2026 is a Thursday, the first page would show:
- Thursday, Friday, Saturday, Sunday, Monday, Tuesday, Wednesday

This is not a standard week view.

## 9. Bookbinding Pattern Verification

### Issue:
The rearrangement pattern needs verification for actual bookbinding. For double-sided printing:
- Pages need to be arranged so that when sheets are folded and bound, they appear in correct order
- The current pattern may not account for front/back printing correctly

## Recommendations

1. **Add input validation** for YEAR and date objects
2. **Add error handling** in all functions, especially file I/O
3. **Fix week alignment** to use actual calendar weeks (Monday-Sunday)
4. **Verify bookbinding pattern** with actual printing requirements
5. **Add logging** for debugging edge cases
6. **Handle empty inputs** gracefully with informative messages
7. **Add unit tests** for edge cases
8. **Consider making SIGNATURE_SIZE a constant** at module level to avoid duplication

