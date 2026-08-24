#!/usr/bin/env bash
# M0: verify ME-AD.zip and selectively extract first-pass files (frozen policy).
set -euo pipefail
SRC=/mnt/g/CERTO-FDI/03_data/public/me_ad/source_v1
DST=/mnt/g/CERTO-FDI/03_data/public/me_ad/extracted_v1
EXPECT_MD5=c74dedb954931034d1870db8cd13e33b
EXPECT_BYTES=10788420015

sz=$(stat -c%s "$SRC/ME-AD.zip")
echo "size=$sz expected=$EXPECT_BYTES"
[ "$sz" -eq "$EXPECT_BYTES" ] || { echo SIZE_MISMATCH; exit 2; }

echo "computing md5..."; md5=$(md5sum "$SRC/ME-AD.zip" | awk '{print $1}')
echo "md5=$md5"; [ "$md5" = "$EXPECT_MD5" ] || { echo MD5_MISMATCH; exit 3; }
echo "computing sha256..."; sha256sum "$SRC/ME-AD.zip" | tee "$SRC/ME-AD.zip.sha256"

echo "zip CRC test (listing errors only)..."
unzip -t "$SRC/ME-AD.zip" > "$SRC/unzip_t_full_log.txt" 2>&1 && echo CRC_PASS || { echo CRC_FAIL; exit 4; }
tail -2 "$SRC/unzip_t_full_log.txt"

mkdir -p "$DST"
unzip -l "$SRC/ME-AD.zip" > "$SRC/zip_listing.txt"
wc -l "$SRC/zip_listing.txt"

echo "selective first-pass extraction..."
unzip -o -q "$SRC/ME-AD.zip" -d "$DST" \
  "*README*" "*Tasks*" "*Pandas*" "*.py" "*requirements*" "*LICENSE*" "*.md" "*.json" "*.yaml" "*.txt" \
  -x "*CSV/*" "*/csv/*" || true
echo "extracted tree:"
find "$DST" -maxdepth 3 | head -50
du -sh "$DST"
echo M0_EXTRACT_DONE
