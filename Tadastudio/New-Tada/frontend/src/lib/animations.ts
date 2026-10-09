// Framer Motion animation variants for consistent animations across the app

export const fadeIn = {
	initial: { opacity: 0 },
	animate: { opacity: 1 },
	exit: { opacity: 0 },
	transition: { duration: 0.2 },
};

export const fadeInUp = {
	initial: { opacity: 0, y: 20 },
	animate: { opacity: 1, y: 0 },
	exit: { opacity: 0, y: 20 },
	transition: { duration: 0.3, ease: "easeOut" },
};

export const fadeInDown = {
	initial: { opacity: 0, y: -20 },
	animate: { opacity: 1, y: 0 },
	exit: { opacity: 0, y: -20 },
	transition: { duration: 0.3, ease: "easeOut" },
};

export const slideInLeft = {
	initial: { x: -100, opacity: 0 },
	animate: { x: 0, opacity: 1 },
	exit: { x: -100, opacity: 0 },
	transition: { duration: 0.3, ease: "easeOut" },
};

export const slideInRight = {
	initial: { x: 100, opacity: 0 },
	animate: { x: 0, opacity: 1 },
	exit: { x: 100, opacity: 0 },
	transition: { duration: 0.3, ease: "easeOut" },
};

export const scaleIn = {
	initial: { scale: 0.9, opacity: 0 },
	animate: { scale: 1, opacity: 1 },
	exit: { scale: 0.9, opacity: 0 },
	transition: { duration: 0.2, ease: "easeOut" },
};
