import React from 'react';

interface LogoProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
  variant?: 'default' | 'icon';
}

export function Logo({ className, variant = 'default', ...props }: LogoProps) {
  if (variant === 'icon') {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 48 48"
        fill="none"
        className={className || "h-8 w-8"}
        {...props}
      >
        <rect width="48" height="48" rx="12" fill="currentColor" fillOpacity="0.1" />
        <path
          d="M 12 16 L 28 16 M 20 16 L 20 32 M 28 20 L 28 26"
          stroke="currentColor"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M 28 32 L 36 32 M 28 16 L 36 16"
          stroke="currentColor"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          strokeOpacity="0.5"
        />
      </svg>
    );
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 48"
      fill="none"
      className={className || "h-8 w-auto"}
      {...props}
    >
      {/* Mark */}
      <rect x="0" y="0" width="48" height="48" rx="12" fill="currentColor" fillOpacity="0.1" />
      <path
        d="M 12 16 L 28 16 M 20 16 L 20 32 M 28 20 L 28 26"
        stroke="currentColor"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M 28 32 L 36 32 M 28 16 L 36 16"
        stroke="currentColor"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        strokeOpacity="0.5"
      />
      
      {/* Typography */}
      <text
        x="60"
        y="32"
        fontFamily="var(--font-heading), 'Space Grotesk', sans-serif"
        fontSize="24"
        fontWeight="600"
        fill="currentColor"
        letterSpacing="-0.02em"
      >
        TutorForge
      </text>
    </svg>
  );
}
