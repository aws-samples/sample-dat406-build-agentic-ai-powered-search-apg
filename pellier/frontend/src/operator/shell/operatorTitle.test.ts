import { operatorTitleForPath } from './OperatorFrame'

describe('operatorTitleForPath', () => {
  it('names the client book at the desk root', () => {
    expect(operatorTitleForPath('/operator')).toBe('Clients · Pellier Operator')
    expect(operatorTitleForPath('/operator/')).toBe('Clients · Pellier Operator')
  })

  it('names nested routes by their surface', () => {
    expect(operatorTitleForPath('/operator/clients/4')).toBe(
      'Client · Pellier Operator',
    )
    expect(operatorTitleForPath('/operator/reviews')).toBe(
      'Action Queue · Pellier Operator',
    )
    expect(operatorTitleForPath('/operator/reviews/12')).toBe(
      'Review · Pellier Operator',
    )
  })
})
