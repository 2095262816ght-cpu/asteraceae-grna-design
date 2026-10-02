import React from 'react'
import activityPulse from '../../assets/generated-icons/activity-pulse.png'
import calculator from '../../assets/generated-icons/calculator.png'
import checkCircle from '../../assets/generated-icons/check-circle.png'

const sources = {
  activity: activityPulse,
  calculator,
  checkCircle,
} as const

export type GeneratedIconName = keyof typeof sources

export const GeneratedIcon: React.FC<{
  name: GeneratedIconName
  className?: string
}> = ({ name, className }) => (
  <img src={sources[name]} alt="" aria-hidden="true" className={className} draggable={false} />
)
