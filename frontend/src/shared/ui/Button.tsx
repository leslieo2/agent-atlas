import Link from "next/link";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost";

type CommonProps = {
  children: ReactNode;
  className?: string;
  variant?: Variant;
};

type ButtonProps = CommonProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    href?: never;
  };

type LinkProps = CommonProps &
  AnchorHTMLAttributes<HTMLAnchorElement> & {
    href: string;
  };

function getClassName(variant: Variant, className?: string) {
  return [styles.button, variant !== "primary" ? styles[variant] : "", className].filter(Boolean).join(" ");
}

export function Button(props: ButtonProps | LinkProps) {
  const variant = props.variant ?? "primary";
  const className = getClassName(variant, props.className);

  if ("href" in props && props.href) {
    const { children, href, className: _className, variant: _variant, ...rest } = props;
    return (
      <Link href={href} className={className} {...rest}>
        {children}
      </Link>
    );
  }

  const buttonProps = props as ButtonProps;
  const { children, className: _className, variant: _variant, type, ...rest } = buttonProps;
  const buttonType = type === "submit" || type === "reset" ? type : "button";
  return (
    <button type={buttonType} className={className} {...rest}>
      {children}
    </button>
  );
}
