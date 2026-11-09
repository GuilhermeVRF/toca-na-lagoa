/** @type {import('tailwindcss').Config} */

// "Azulejo modernista" palette, after the tiles and buildings around the Pampulha lagoon:
// cobalt tile blue, whitewash (cal) and ink, with ochre as the only warm accent.
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Figtree', 'system-ui', 'sans-serif'],
        display: ['"Bricolage Grotesque"', 'Figtree', 'system-ui', 'sans-serif'],
      },
      colors: {
        white: '#FFFDF8',
        cobalto: {
          50: '#EEF2FA',
          100: '#DCE4F5',
          200: '#C3D1F2',
          300: '#A2B8EE',
          400: '#7491DF',
          500: '#4767C4',
          600: '#2F4FA8',
          700: '#22408F',
          800: '#1A3275',
          900: '#14275C',
          950: '#0E1A40',
        },
        // Warm whitewash on the light end, night indigo (anil) on the dark end.
        tinta: {
          50: '#F5EFE3',
          100: '#ECE5D6',
          200: '#DED4C0',
          300: '#C4BBA8',
          400: '#94919A',
          500: '#5E6482',
          600: '#454E78',
          700: '#2A3766',
          800: '#1B2545',
          900: '#16214A',
          950: '#0E1630',
        },
        ocre: {
          50: '#FBF3E2',
          100: '#F6E4BE',
          200: '#EECF8E',
          300: '#E5B65C',
          400: '#E0A73E',
          500: '#C98A1B',
          600: '#A8710F',
          700: '#86580C',
          800: '#64420B',
          900: '#432C07',
        },
        barro: {
          50: '#FBEDE8',
          100: '#F5D3C7',
          200: '#EBAE99',
          300: '#E08A70',
          400: '#D06A4D',
          500: '#B4452F',
          600: '#963624',
          700: '#76291C',
        },
        folha: {
          100: '#DCEFD9',
          300: '#8FCB89',
          400: '#5DAE5A',
          500: '#3C8F42',
          700: '#2A6430',
        },
      },
    },
  },
};
