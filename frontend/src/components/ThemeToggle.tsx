/**
 * Theme Toggle Button - Sun/Moon icon toggle
 * Place in: src/components/ThemeToggle.tsx
 */
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className="p-2.5 rounded-full 
               bg-gray-100 dark:bg-gray-800 
               hover:bg-gray-200 dark:hover:bg-gray-700
               border border-gray-200 dark:border-gray-700
               transition-all duration-300 hover:scale-110 group"
      aria-label="Toggle theme"
    >
      {theme === 'light' ? (
        <Moon className="h-5 w-5 text-gray-700 dark:text-gray-300 
                        group-hover:text-purple-600 dark:group-hover:text-purple-400
                        transition-colors duration-300" 
              strokeWidth={2} />
      ) : (
        <Sun className="h-5 w-5 text-gray-300 dark:text-gray-300
                       group-hover:text-amber-400 dark:group-hover:text-amber-400
                       transition-colors duration-300" 
             strokeWidth={2} />
      )}
    </button>
  )
}

export default ThemeToggle