import {
  useEffect,
  useState,
  type ImgHTMLAttributes,
} from 'react'
import {
  imageSrc,
  responsiveImageSrcSet,
} from '../utils/assetPath'

interface ResponsiveImageProps
  extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'srcSet'> {
  src: string
  widths?: readonly number[]
  pictureClassName?: string
}

/**
 * AVIF-first local image delivery with WebP and original-file fallbacks.
 * External URLs render through the fallback image without invented variants.
 */
export default function ResponsiveImage({
  src,
  widths = [480, 960],
  sizes,
  pictureClassName,
  onError,
  fetchPriority,
  ...imageProps
}: ResponsiveImageProps) {
  const avifSrcSet = responsiveImageSrcSet(src, widths, 'avif')
  const webpSrcSet = responsiveImageSrcSet(src, widths, 'webp')
  const hasResponsiveVariants = Boolean(avifSrcSet || webpSrcSet)
  const [variantsEnabled, setVariantsEnabled] = useState(hasResponsiveVariants)

  useEffect(() => {
    setVariantsEnabled(hasResponsiveVariants)
  }, [hasResponsiveVariants, src])

  return (
    <picture className={pictureClassName}>
      {variantsEnabled && avifSrcSet ? (
        <source type="image/avif" srcSet={avifSrcSet} sizes={sizes} />
      ) : null}
      {variantsEnabled && webpSrcSet ? (
        <source type="image/webp" srcSet={webpSrcSet} sizes={sizes} />
      ) : null}
      <img
        key={variantsEnabled ? 'responsive' : 'original'}
        src={imageSrc(src)}
        sizes={sizes}
        onError={(event) => {
          if (variantsEnabled) {
            setVariantsEnabled(false)
            return
          }
          onError?.(event)
        }}
        {...(fetchPriority ? { fetchpriority: fetchPriority } : {})}
        {...imageProps}
      />
    </picture>
  )
}
