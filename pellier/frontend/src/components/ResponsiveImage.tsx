import { type ImgHTMLAttributes } from 'react';
import {
  imageSrc,
  responsiveImageSrcSet,
} from '../utils/assetPath';

interface ResponsiveImageProps
  extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'srcSet'> {
  src: string;
  widths?: readonly number[];
  pictureClassName?: string;
}

/**
 * Prefer local AVIF and WebP derivatives. The shipped fallback is WebP rather
 * than a duplicate PNG source master.
 */
export default function ResponsiveImage({
  src,
  widths = [480, 960],
  sizes,
  pictureClassName,
  ...imageProps
}: ResponsiveImageProps) {
  const avifSrcSet = responsiveImageSrcSet(src, widths, 'avif');
  const webpSrcSet = responsiveImageSrcSet(src, widths, 'webp');

  return (
    <picture className={pictureClassName}>
      {avifSrcSet ? (
        <source type="image/avif" srcSet={avifSrcSet} sizes={sizes} />
      ) : null}
      {webpSrcSet ? (
        <source type="image/webp" srcSet={webpSrcSet} sizes={sizes} />
      ) : null}
      <img
        src={imageSrc(src)}
        srcSet={webpSrcSet}
        sizes={sizes}
        {...imageProps}
      />
    </picture>
  );
}
