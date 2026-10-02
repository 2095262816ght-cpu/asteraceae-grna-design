import React from 'react'
import dnaBrand from '../../assets/generated-icons/dna-brand.png'
import dnaGene from '../../assets/generated-icons/dna-gene.png'

export const DnaHelix: React.FC<{
  className?: string
  variant?: 'brand' | 'gene'
}> = ({
  className,
  variant = 'gene',
}) => (
  <img
    src={variant === 'brand' ? dnaBrand : dnaGene}
    alt=""
    className={className}
    aria-hidden="true"
    draggable={false}
  />
)
