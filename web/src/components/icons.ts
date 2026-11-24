// Every icon the app can draw (Material Symbols, outlined, weight 400). Each SVG is
// bundled on its own, so only icons listed here ship. Keep the imports and the ICONS
// entries in alphabetical order (icons.test.ts checks).
import type { FC, SVGProps } from 'react'
import AddIcon from '@material-symbols/svg-400/outlined/add.svg?react'
import ArrowDownwardIcon from '@material-symbols/svg-400/outlined/arrow_downward.svg?react'
import ArrowUpwardIcon from '@material-symbols/svg-400/outlined/arrow_upward.svg?react'
import BrightnessAutoIcon from '@material-symbols/svg-400/outlined/brightness_auto.svg?react'
import CancelIcon from '@material-symbols/svg-400/outlined/cancel.svg?react'
import ChangeHistoryIcon from '@material-symbols/svg-400/outlined/change_history.svg?react'
import ChangeHistoryFillIcon from '@material-symbols/svg-400/outlined/change_history-fill.svg?react'
import CheckCircleIcon from '@material-symbols/svg-400/outlined/check_circle.svg?react'
import ChevronLeftIcon from '@material-symbols/svg-400/outlined/chevron_left.svg?react'
import CloseIcon from '@material-symbols/svg-400/outlined/close.svg?react'
import DarkModeIcon from '@material-symbols/svg-400/outlined/dark_mode.svg?react'
import DeleteIcon from '@material-symbols/svg-400/outlined/delete.svg?react'
import DescriptionIcon from '@material-symbols/svg-400/outlined/description.svg?react'
import DownloadIcon from '@material-symbols/svg-400/outlined/download.svg?react'
import EditIcon from '@material-symbols/svg-400/outlined/edit.svg?react'
import ErrorIcon from '@material-symbols/svg-400/outlined/error.svg?react'
import FolderIcon from '@material-symbols/svg-400/outlined/folder.svg?react'
import FolderFillIcon from '@material-symbols/svg-400/outlined/folder-fill.svg?react'
import GavelIcon from '@material-symbols/svg-400/outlined/gavel.svg?react'
import HomeIcon from '@material-symbols/svg-400/outlined/home.svg?react'
import HomeFillIcon from '@material-symbols/svg-400/outlined/home-fill.svg?react'
import HowToVoteIcon from '@material-symbols/svg-400/outlined/how_to_vote.svg?react'
import InfoIcon from '@material-symbols/svg-400/outlined/info.svg?react'
import KeyboardArrowDownIcon from '@material-symbols/svg-400/outlined/keyboard_arrow_down.svg?react'
import LightModeIcon from '@material-symbols/svg-400/outlined/light_mode.svg?react'
import LinkIcon from '@material-symbols/svg-400/outlined/link.svg?react'
import LoginIcon from '@material-symbols/svg-400/outlined/login.svg?react'
import LogoutIcon from '@material-symbols/svg-400/outlined/logout.svg?react'
import MenuBookIcon from '@material-symbols/svg-400/outlined/menu_book.svg?react'
import MoreVertIcon from '@material-symbols/svg-400/outlined/more_vert.svg?react'
import OpenInNewIcon from '@material-symbols/svg-400/outlined/open_in_new.svg?react'
import PersonIcon from '@material-symbols/svg-400/outlined/person.svg?react'
import PersonFillIcon from '@material-symbols/svg-400/outlined/person-fill.svg?react'
import ProgressActivityIcon from '@material-symbols/svg-400/outlined/progress_activity.svg?react'
import RefreshIcon from '@material-symbols/svg-400/outlined/refresh.svg?react'
import SearchIcon from '@material-symbols/svg-400/outlined/search.svg?react'
import UndoIcon from '@material-symbols/svg-400/outlined/undo.svg?react'
import UploadIcon from '@material-symbols/svg-400/outlined/upload.svg?react'
import VisibilityIcon from '@material-symbols/svg-400/outlined/visibility.svg?react'
import WarningIcon from '@material-symbols/svg-400/outlined/warning.svg?react'

type Svg = FC<SVGProps<SVGSVGElement>>

export const ICONS = {
  add: AddIcon,
  arrow_downward: ArrowDownwardIcon,
  arrow_upward: ArrowUpwardIcon,
  brightness_auto: BrightnessAutoIcon,
  cancel: CancelIcon,
  change_history: ChangeHistoryIcon,
  check_circle: CheckCircleIcon,
  chevron_left: ChevronLeftIcon,
  close: CloseIcon,
  dark_mode: DarkModeIcon,
  delete: DeleteIcon,
  description: DescriptionIcon,
  download: DownloadIcon,
  edit: EditIcon,
  error: ErrorIcon,
  folder: FolderIcon,
  gavel: GavelIcon,
  home: HomeIcon,
  how_to_vote: HowToVoteIcon,
  info: InfoIcon,
  keyboard_arrow_down: KeyboardArrowDownIcon,
  light_mode: LightModeIcon,
  link: LinkIcon,
  login: LoginIcon,
  logout: LogoutIcon,
  menu_book: MenuBookIcon,
  more_vert: MoreVertIcon,
  open_in_new: OpenInNewIcon,
  person: PersonIcon,
  progress_activity: ProgressActivityIcon,
  refresh: RefreshIcon,
  search: SearchIcon,
  undo: UndoIcon,
  upload: UploadIcon,
  visibility: VisibilityIcon,
  warning: WarningIcon,
} satisfies Record<string, Svg>

export type IconName = keyof typeof ICONS

/** Filled variants: the active tab's icon. */
export const FILLED: Partial<Record<IconName, Svg>> = {
  change_history: ChangeHistoryFillIcon,
  folder: FolderFillIcon,
  home: HomeFillIcon,
  person: PersonFillIcon,
}
