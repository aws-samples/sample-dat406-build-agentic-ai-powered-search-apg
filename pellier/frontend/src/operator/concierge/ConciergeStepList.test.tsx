import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ConciergeStepList from './ConciergeStepList'

describe('ConciergeStepList', () => {
  it('names a step status for assistive technology instead of relying on its icon', () => {
    render(
      <ConciergeStepList
        steps={[
          {
            kind: 'case_investigator',
            label: 'Investigate the client case',
            source: 'Strands Graph',
            status: 'failed',
            result: 'The evidence source was unavailable.',
          },
        ]}
      />,
    )

    expect(screen.getByText('Status: Failed')).toHaveClass('sr-only')
  })
})
