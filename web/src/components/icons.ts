// Every icon the app can draw (Material Symbols, outlined, weight 400). Each SVG is
// bundled on its own, so only icons listed here ship. Keep the imports and the ICONS
// entries in alphabetical order (icons.test.ts checks).
import type { FC, SVGProps } from 'react'
import AddIcon from '@material-symbols/svg-400/outlined/add.svg?react'
import ArrowDownwardIcon from '@material-symbols/svg-400/outlined/arrow_downward.svg?react'
import ArrowUpwardIcon from '@material-symbols/svg-400/outlined/arrow_upward.svg?react'
import BarChartIcon from '@material-symbols/svg-400/outlined/bar_chart.svg?react'
import BrightnessAutoIcon from '@material-symbols/svg-400/outlined/brightness_auto.svg?react'
import CancelIcon from '@material-symbols/svg-400/outlined/cancel.svg?react'
import ChangeHistoryIcon from '@material-symbols/svg-400/outlined/change_history.svg?react'
import ChangeHistoryFillIcon from '@material-symbols/svg-400/outlined/change_history-fill.svg?react'
import CheckCircleIcon from '@material-symbols/svg-400/outlined/check_circle.svg?react'
import ChevronLeftIcon from '@material-symbols/svg-400/outlined/chevron_left.svg?react'
import ChevronRightIcon from '@material-symbols/svg-400/outlined/chevron_right.svg?react'
import CloseIcon from '@material-symbols/svg-400/outlined/close.svg?react'
import ContentCopyIcon from '@material-symbols/svg-400/outlined/content_copy.svg?react'
import DarkModeIcon from '@material-symbols/svg-400/outlined/dark_mode.svg?react'
import DeleteIcon from '@material-symbols/svg-400/outlined/delete.svg?react'
import DescriptionIcon from '@material-symbols/svg-400/outlined/description.svg?react'
import DownloadIcon from '@material-symbols/svg-400/outlined/download.svg?react'
import EditIcon from '@material-symbols/svg-400/outlined/edit.svg?react'
import ErrorIcon from '@material-symbols/svg-400/outlined/error.svg?react'
import FlagIcon from '@material-symbols/svg-400/outlined/flag.svg?react'
import FolderIcon from '@material-symbols/svg-400/outlined/folder.svg?react'
import FolderFillIcon from '@material-symbols/svg-400/outlined/folder-fill.svg?react'
import ForumIcon from '@material-symbols/svg-400/outlined/forum.svg?react'
import ForumFillIcon from '@material-symbols/svg-400/outlined/forum-fill.svg?react'
import FullscreenIcon from '@material-symbols/svg-400/outlined/fullscreen.svg?react'
import FullscreenExitIcon from '@material-symbols/svg-400/outlined/fullscreen_exit.svg?react'
import GavelIcon from '@material-symbols/svg-400/outlined/gavel.svg?react'
import HistoryIcon from '@material-symbols/svg-400/outlined/history.svg?react'
import HomeIcon from '@material-symbols/svg-400/outlined/home.svg?react'
import HomeFillIcon from '@material-symbols/svg-400/outlined/home-fill.svg?react'
import HowToVoteIcon from '@material-symbols/svg-400/outlined/how_to_vote.svg?react'
import HowToVoteFillIcon from '@material-symbols/svg-400/outlined/how_to_vote-fill.svg?react'
import InfoIcon from '@material-symbols/svg-400/outlined/info.svg?react'
import KeyIcon from '@material-symbols/svg-400/outlined/key.svg?react'
import KeyboardArrowDownIcon from '@material-symbols/svg-400/outlined/keyboard_arrow_down.svg?react'
import LanguageIcon from '@material-symbols/svg-400/outlined/language.svg?react'
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
import SmartToyIcon from '@material-symbols/svg-400/outlined/smart_toy.svg?react'
import UndoIcon from '@material-symbols/svg-400/outlined/undo.svg?react'
import UnfoldLessIcon from '@material-symbols/svg-400/outlined/unfold_less.svg?react'
import UnfoldMoreIcon from '@material-symbols/svg-400/outlined/unfold_more.svg?react'
import UploadIcon from '@material-symbols/svg-400/outlined/upload.svg?react'
import VisibilityIcon from '@material-symbols/svg-400/outlined/visibility.svg?react'
import VolumeUpIcon from '@material-symbols/svg-400/outlined/volume_up.svg?react'
import WarningIcon from '@material-symbols/svg-400/outlined/warning.svg?react'
import WrapTextIcon from '@material-symbols/svg-400/outlined/wrap_text.svg?react'

type Svg = FC<SVGProps<SVGSVGElement>>

export const ICONS = {
  add: AddIcon,
  arrow_downward: ArrowDownwardIcon,
  arrow_upward: ArrowUpwardIcon,
  bar_chart: BarChartIcon,
  brightness_auto: BrightnessAutoIcon,
  cancel: CancelIcon,
  change_history: ChangeHistoryIcon,
  check_circle: CheckCircleIcon,
  chevron_left: ChevronLeftIcon,
  chevron_right: ChevronRightIcon,
  close: CloseIcon,
  content_copy: ContentCopyIcon,
  dark_mode: DarkModeIcon,
  delete: DeleteIcon,
  description: DescriptionIcon,
  download: DownloadIcon,
  edit: EditIcon,
  error: ErrorIcon,
  flag: FlagIcon,
  folder: FolderIcon,
  forum: ForumIcon,
  fullscreen: FullscreenIcon,
  fullscreen_exit: FullscreenExitIcon,
  gavel: GavelIcon,
  history: HistoryIcon,
  home: HomeIcon,
  how_to_vote: HowToVoteIcon,
  info: InfoIcon,
  key: KeyIcon,
  keyboard_arrow_down: KeyboardArrowDownIcon,
  language: LanguageIcon,
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
  smart_toy: SmartToyIcon,
  undo: UndoIcon,
  unfold_less: UnfoldLessIcon,
  unfold_more: UnfoldMoreIcon,
  upload: UploadIcon,
  visibility: VisibilityIcon,
  volume_up: VolumeUpIcon,
  warning: WarningIcon,
  wrap_text: WrapTextIcon,
} satisfies Record<string, Svg>

export type IconName = keyof typeof ICONS

/** Filled variants: the active tab's icon. */
export const FILLED: Partial<Record<IconName, Svg>> = {
  change_history: ChangeHistoryFillIcon,
  folder: FolderFillIcon,
  forum: ForumFillIcon,
  home: HomeFillIcon,
  how_to_vote: HowToVoteFillIcon,
  person: PersonFillIcon,
}
