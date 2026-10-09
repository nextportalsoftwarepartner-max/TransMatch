/** Permission codes, one per menu / screen (TM_MST_PERMISSION.VCH_PERMISSION_CODE). */
export const PERMISSIONS = {
  TRN: 'TRN',
  TRN_PDF_UPLOAD: 'TRN_PDF_UPLOAD',
  TRN_MANUAL_INPUT: 'TRN_MANUAL_INPUT',
  TRN_IMAGE_UPLOAD: 'TRN_IMAGE_UPLOAD',
  TRN_DATA_ENRICHMENT: 'TRN_DATA_ENRICHMENT',
  ADM: 'ADM',
  ADM_USER_GROUP: 'ADM_USER_GROUP',
  ADM_USER_ROLE: 'ADM_USER_ROLE',
  ADM_USER_RIGHTS: 'ADM_USER_RIGHTS',
  ADM_USER_PROFILE: 'ADM_USER_PROFILE',
  ADM_CUSTOMER_PROFILE: 'ADM_CUSTOMER_PROFILE',
  ADM_BANK_PROFILE: 'ADM_BANK_PROFILE',
  ADM_BLACKLISTED: 'ADM_BLACKLISTED',
  ADM_SUSPICIOUS: 'ADM_SUSPICIOUS',
  RPT: 'RPT',
  RPT_ENQUIRY: 'RPT_ENQUIRY',
  RPT_KPI_REVIEW: 'RPT_KPI_REVIEW',
} as const;

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

/** Positions of the flags in CHR_ACCESS_RIGHTS, e.g. "11110000". */
export const ACCESS_RIGHTS = ['VIEW', 'CREATE', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT', 'PUBLISH', 'ARCHIVE'] as const;
export type AccessRight = (typeof ACCESS_RIGHTS)[number];

export const NO_RIGHTS = '00000000';
export const FULL_CRUD_RIGHTS = '11110000';

export function hasRight(rights: string | undefined, right: AccessRight): boolean {
  return rights?.[ACCESS_RIGHTS.indexOf(right)] === '1';
}

export function buildRights(granted: AccessRight[]): string {
  return ACCESS_RIGHTS.map((r) => (granted.includes(r) ? '1' : '0')).join('');
}

/** Combines the rights a user holds through several roles. */
export function mergeRights(a: string, b: string): string {
  return ACCESS_RIGHTS.map((_, i) => (a[i] === '1' || b[i] === '1' ? '1' : '0')).join('');
}

export interface SessionUser {
  userId: string;
  loginId: string;
  userName: string;
  /** Super users bypass permission checks. */
  isSuperUser: boolean;
  /** Permission code -> access rights string. */
  permissions: Record<string, string>;
}

export function can(user: SessionUser | null | undefined, code: PermissionCode, right: AccessRight = 'VIEW'): boolean {
  if (!user) return false;
  return user.isSuperUser || hasRight(user.permissions[code], right);
}

export interface NavItem {
  code: PermissionCode;
  label: string;
  href: string;
}
export interface NavSection {
  code: PermissionCode;
  label: string;
  items: NavItem[];
}

/** Menu structure of the application, in display order. */
export const NAVIGATION: NavSection[] = [
  {
    code: PERMISSIONS.TRN,
    label: 'Transaction',
    items: [
      { code: PERMISSIONS.TRN_PDF_UPLOAD, label: 'Docx Upload', href: '/transactions/pdf-upload' },
      { code: PERMISSIONS.TRN_MANUAL_INPUT, label: 'Manual Data Input', href: '/transactions/manual-input' },
      { code: PERMISSIONS.TRN_IMAGE_UPLOAD, label: 'Image Upload', href: '/transactions/image-upload' },
      { code: PERMISSIONS.TRN_DATA_ENRICHMENT, label: 'Data Enrichment', href: '/transactions/data-enrichment' },
    ],
  },
  {
    code: PERMISSIONS.ADM,
    label: 'Administration',
    items: [
      { code: PERMISSIONS.ADM_USER_GROUP, label: 'User Group', href: '/administration/user-groups' },
      { code: PERMISSIONS.ADM_USER_ROLE, label: 'User Role', href: '/administration/user-roles' },
      { code: PERMISSIONS.ADM_USER_RIGHTS, label: 'User Rights', href: '/administration/user-rights' },
      { code: PERMISSIONS.ADM_USER_PROFILE, label: 'User Profile', href: '/administration/user-profiles' },
      { code: PERMISSIONS.ADM_CUSTOMER_PROFILE, label: 'Customer Profile', href: '/administration/customers' },
      { code: PERMISSIONS.ADM_BANK_PROFILE, label: 'Bank Profile', href: '/administration/banks' },
      { code: PERMISSIONS.ADM_BLACKLISTED, label: 'Blacklisted', href: '/administration/blacklisted' },
      { code: PERMISSIONS.ADM_SUSPICIOUS, label: 'Suspicious', href: '/administration/suspicious' },
    ],
  },
  {
    code: PERMISSIONS.RPT,
    label: 'Report / Enquiry',
    items: [
      { code: PERMISSIONS.RPT_ENQUIRY, label: 'Enquiry / Generate Report', href: '/reports/enquiry' },
      { code: PERMISSIONS.RPT_KPI_REVIEW, label: 'KPI Review', href: '/reports/kpi-review' },
    ],
  },
];
