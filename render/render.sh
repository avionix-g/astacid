#! /usr/bin/env zsh

font1=$1
font2=$2
sample_text=$3
size=100

echo "Rendering $sample_text using $font1..."

convert +antialias -density 228 -fill red -font $font2 -pointsize $size label:@$sample_text $font2.webp
convert +antialias -density 228 -fill green -font $font1 -pointsize $size label:@$sample_text $font1.webp
convert $font2.webp $font1.webp -compose multiply -composite $font2-comparison-large.webp
convert -resize 50% $font2-comparison-large.webp $font2-comparison.webp

rm $font2.webp $font1.webp $font2-comparison-large.webp

echo "Rendered $sample_text to $font2-comparison.webp"
