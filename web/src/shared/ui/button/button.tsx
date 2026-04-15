import React from 'react'
import clsx from 'clsx'
import './button.scss'

export type ButtonVariant = 'primary' | 'default' | 'outline' | 'link'
export type ButtonTheme = 'theme' | 'info' | 'warning' | 'default'
export type ButtonSize = 'lg' | 'md' | 'sm'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  theme?: ButtonTheme
  size?: ButtonSize
  block?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const AppButton = React.forwardRef<HTMLButtonElement, ButtonProps>(({
  variant = 'primary',
  theme = 'theme',
  size = 'md',
  block = false,
  leftIcon,
  rightIcon,
  children,
  type = 'button',
  className,
  ...rest
}, ref) => {
  const classes = clsx(
    'app-button',
    `v-${variant}`,
    `t-${theme}`,
    `s-${size}`,
    { disabled: rest.disabled, block },
    className
  )

  return (
    <button ref={ref} type={type} className={classes} {...rest}>
      {leftIcon ? <span className="app-button__icon left">{leftIcon}</span> : null}
      {children ? <span className="app-button__label">{children}</span> : null}
      {rightIcon ? <span className="app-button__icon right">{rightIcon}</span> : null}
    </button>
  )
})

export default AppButton
