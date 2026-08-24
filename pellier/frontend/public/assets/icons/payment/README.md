# Payment marks

The storefront footer uses official payment-brand artwork inside Pellier's
non-processing demo checkout. The footer and checkout both state that no payment
is processed. These marks make the simulated commerce flow recognizable; they
do not claim that this sample accepts a card or wallet.

## Asset manifest

| File | Mark | Owner-hosted source | Notice |
| --- | --- | --- | --- |
| `visa.svg` | Visa | Visa corporate site and brand standards | `VISA-LICENSE.txt` |
| `mastercard.svg` | Mastercard | Mastercard corporate site | `MASTERCARD-LICENSE.txt` |
| `amex.svg` | American Express | American Express static assets | `AMEX-LICENSE.txt` |
| `paypal.svg` | PayPal | PayPal UI asset host | `PAYPAL-LICENSE.txt` |
| `apple-pay.svg` | Apple Pay | Apple Pay marketing resources | `APPLE-PAY-LICENSE.txt` |
| `google-pay.svg` | Google Pay | Google Pay brand resources | `GOOGLE-PAY-LICENSE.txt` |

Each notice records the exact source, owner, use boundary, and any canvas-only
normalization. The marks are not licensed under this repository's MIT License.

## Artwork contract

- Use only owner-hosted artwork and preserve the supplied mark, proportions, and
  colors.
- Canvas-only changes may remove fixed dimensions or crop transparent padding.
  Do not redraw or restyle a mark.
- Preserve owner-supplied outlines and backgrounds that are part of the mark.
  Apple Pay and Google Pay require those treatments.
- Every SVG has a `viewBox` and no fixed `width` or `height`.
- Do not add raster fallbacks.
- A production deployment may show only methods it actually accepts and must
  follow each owner's current brand requirements.

## Footer contract

- `src/components/Footer.test.tsx` fixes the six-mark set, its accessible
  labels, exact public paths, and the adjacent no-charge disclosure.
- Add each SVG and its sibling notice in the same source commit. A production
  deployment may use only methods it actually accepts.
