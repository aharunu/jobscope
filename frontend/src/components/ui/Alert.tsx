import React from 'react';
import { InfoIcon, WarningIcon, WarningCircleIcon } from './icons';

export interface AlertProps {
  variant?: 'danger' | 'warning' | 'info';
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({ variant = 'info', title, children, className = '' }) => {
  const Icon = variant === 'danger' ? WarningCircleIcon : variant === 'warning' ? WarningIcon : InfoIcon;
  return <div role="alert" className={`alert-banner alert-${variant} ${className}`}>
    <Icon size={19} className="alert-icon" aria-hidden="true" />
    <div className="alert-copy">{title && <strong>{title}</strong>}<div>{children}</div></div>
  </div>;
};
