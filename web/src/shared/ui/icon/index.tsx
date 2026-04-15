import clsx from "clsx";
import type { SVGProps } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  Ban,
  Boxes,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  Clapperboard,
  Copy,
  Download,
  Eye,
  EyeOff,
  Ellipsis,
  Expand,
  FileText,
  FolderOpen,
  History,
  House,
  Image,
  Keyboard,
  LoaderCircle,
  Lock,
  LockOpen,
  LogOut,
  Mail,
  Map,
  MessageCircleMore,
  MousePointerClick,
  PackageOpen,
  Phone,
  Play,
  Plus,
  ReceiptText,
  ScanSearch,
  Search,
  Settings,
  Square,
  Sparkles,
  Trash2,
  Upload,
  User,
  Wallet,
  X,
  type LucideIcon,
  type LucideProps,
} from "lucide-react";
import "./index.scss";

export type AppIconProps = LucideProps;

const DEFAULT_STROKE_WIDTH = 1.85;

function withAppIcon(Icon: LucideIcon) {
  return function AppIcon({
    className,
    strokeWidth = DEFAULT_STROKE_WIDTH,
    ...props
  }: AppIconProps) {
    return (
      <Icon
        {...props}
        className={clsx("app-icon", className)}
        strokeWidth={strokeWidth}
      />
    );
  };
}

export const ArrowLeftIcon = withAppIcon(ArrowLeft);
export const ArrowRightIcon = withAppIcon(ArrowRight);
export const ArrowUpRightIcon = withAppIcon(ArrowUpRight);
export const AudioLinesIcon = withAppIcon(AudioLines);
export const BanIcon = withAppIcon(Ban);
export const BoxesIcon = withAppIcon(Boxes);
export const CheckIcon = withAppIcon(Check);
export const ChevronDownIcon = withAppIcon(ChevronDown);
export const CircleAlertIcon = withAppIcon(CircleAlert);
export const CircleCheckIcon = withAppIcon(CircleCheck);
export const CircleHelpIcon = withAppIcon(CircleHelp);
export const ClapperboardIcon = withAppIcon(Clapperboard);
export const CopyIcon = withAppIcon(Copy);
export const DownloadIcon = withAppIcon(Download);
export const EyeIcon = withAppIcon(Eye);
export const EyeOffIcon = withAppIcon(EyeOff);
export const EllipsisIcon = withAppIcon(Ellipsis);
export const ExpandIcon = withAppIcon(Expand);
export const FileTextIcon = withAppIcon(FileText);
export const FolderOpenIcon = withAppIcon(FolderOpen);
export const HistoryIcon = withAppIcon(History);
export const HouseIcon = withAppIcon(House);
export const ImageIcon = withAppIcon(Image);
export const KeyboardIcon = withAppIcon(Keyboard);
export const LoaderCircleIcon = withAppIcon(LoaderCircle);
export const LockIcon = withAppIcon(Lock);
export const LockOpenIcon = withAppIcon(LockOpen);
export const LogOutIcon = withAppIcon(LogOut);
export const MailIcon = withAppIcon(Mail);
export const MapIcon = withAppIcon(Map);
export const MessageCircleMoreIcon = withAppIcon(MessageCircleMore);
export const MousePointerClickIcon = withAppIcon(MousePointerClick);
export const PackageOpenIcon = withAppIcon(PackageOpen);
export const PhoneIcon = withAppIcon(Phone);
export const PlayIcon = withAppIcon(Play);
export const PlusIcon = withAppIcon(Plus);
export const ReceiptTextIcon = withAppIcon(ReceiptText);
export const ScanSearchIcon = withAppIcon(ScanSearch);
export const SearchIcon = withAppIcon(Search);
export const SettingsIcon = withAppIcon(Settings);
export const SquareIcon = withAppIcon(Square);
export const SparklesIcon = withAppIcon(Sparkles);
export const Trash2Icon = withAppIcon(Trash2);
export const UploadIcon = withAppIcon(Upload);
export const UserIcon = withAppIcon(User);
export const WalletIcon = withAppIcon(Wallet);
export const XIcon = withAppIcon(X);

export function WeChatIcon({
  className,
  ...props
}: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className={clsx("app-icon", className)}
      aria-hidden="true"
      {...props}
    >
      <path
        d="M10.1 5C6.73 5 4 7.33 4 10.2c0 1.61.86 3.04 2.22 3.98L5.6 16.8l2.78-1.38c.55.12 1.12.18 1.72.18 3.37 0 6.1-2.33 6.1-5.2S13.47 5 10.1 5Z"
        stroke="currentColor"
        strokeWidth="1.85"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M15.44 10.2c2.52 0 4.56 1.73 4.56 3.86 0 1.17-.62 2.22-1.61 2.94l.45 2-2.11-1.06c-.42.09-.85.14-1.29.14-2.52 0-4.56-1.73-4.56-3.86s2.04-3.86 4.56-3.86Z"
        stroke="currentColor"
        strokeWidth="1.85"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8.1" cy="9.9" r="0.85" fill="currentColor" />
      <circle cx="12.1" cy="9.9" r="0.85" fill="currentColor" />
      <circle cx="14.2" cy="14.2" r="0.75" fill="currentColor" />
      <circle cx="17.25" cy="14.2" r="0.75" fill="currentColor" />
    </svg>
  );
}
