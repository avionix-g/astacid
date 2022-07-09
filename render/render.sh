#! /usr/bin/env zsh

input="sample.txt"
target="AstacidMono"
size=100
declare -a bases=("DejaVuSansMono", "DejaVuSansMono-Bront")

for base in "${bases[@]}"
do
   echo "Rendering $input using $base..."

   convert +antialias -density 228 -fill red -font $base.ttf -pointsize $size label:@$input $base.webp
   convert +antialias -density 228 -fill green -font $target.ttf -pointsize $size label:@$input $target.webp
   convert $target.webp $base.webp -compose multiply -composite $base-comparison-large.webp
   convert -resize 25% $base-comparison-large.webp $base-comparison.webp
   rm $base.webp $target.webp $base-comparison-large.webp

   echo "Rendered $input to $base-comparison.webp"
done
