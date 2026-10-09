// Shapes returned by the API.

import type { WatchStatus } from './classification.js';

export interface AuditInfo {
  createdAt: string;
  createdBy: string | null;
  modifiedAt: string | null;
  modifiedBy: string | null;
}

export interface GroupDto extends AuditInfo {
  groupId: string;
  groupName: string;
  groupDesc: string | null;
  status: 'A' | 'I';
  noDelete: boolean;
}

export interface RoleDto extends AuditInfo {
  roleId: string;
  groupId: string;
  groupName: string;
  roleName: string;
  roleDesc: string | null;
  status: 'A' | 'I';
  noDelete: boolean;
}

export interface PermissionDto {
  permissionId: string;
  code: string;
  name: string;
  description: string | null;
  parentPermissionId: string | null;
  mainMenu: boolean;
  displayOrder: number;
}

export interface RolePermissionDto {
  permissionId: string;
  rights: string;
}

export interface UserDto extends AuditInfo {
  userId: string;
  loginId: string;
  userName: string;
  email: string | null;
  contactNo: string | null;
  address1: string | null;
  address2: string | null;
  address3: string | null;
  address4: string | null;
  supervisorUserId: string | null;
  supervisorName: string | null;
  groupId: string | null;
  groupName: string | null;
  roleId: string | null;
  roleName: string | null;
  noDelete: boolean;
}

export interface CustomerDto extends AuditInfo {
  customerId: string;
  customerCode: string;
  customerName: string;
  email: string | null;
  contactNo: string | null;
  address: string | null;
  remark: string | null;
}

export interface BankDto extends AuditInfo {
  bankId: string;
  bankName: string;
  bankDisplayName: string | null;
  bankRegNo: string | null;
  bankAddress: string | null;
}

export interface WatchNameDto extends AuditInfo {
  id: string;
  name: string;
  /** Suspicious names only: whether the same name is also blacklisted. */
  existsInBlacklisted?: boolean;
}

export interface OptionDto {
  value: string;
  label: string;
}

export interface BankTemplateDto {
  id: number;
  name: string;
}

/** A statement read from an uploaded PDF, ready to be reviewed and saved. */
export interface StatementPreviewDto {
  fileName: string;
  bankTemplate: string;
  bankName: string;
  bankRegistrationNo: string;
  bankAddress: string;
  customerCode: string;
  /** True when the customer name is already on file, so the code is known. */
  customerKnown: boolean;
  customerName: string;
  customerAddress: string;
  statementDate: string | null;
  accountNumber: string;
  transactions: StatementPreviewRowDto[];
}

export interface StatementPreviewRowDto {
  /** ISO date, or null when the date printed on the statement could not be read. */
  transactionDate: string | null;
  rawDate: string;
  description: string;
  descriptionOthers: string;
  targetName: string;
  creditAmount: number;
  debitAmount: number;
  statementBalance: number;
}

export interface TransactionListRowDto {
  transactionId: string;
  customerCode: string;
  customerName: string;
  accountNo: string | null;
  targetName: string | null;
  fileName: string | null;
  description: string;
  transactionDate: string;
  entryDate: string;
}

export interface TransactionDetailDto {
  transactionId: string;
  fileName: string | null;
  bankId: string;
  customerId: string;
  agentUserId: string;
  accountNo: string | null;
  statementDate: string | null;
  transactionDate: string;
  description: string | null;
  descriptionOthers: string | null;
  targetName: string | null;
  creditAmount: number;
  debitAmount: number;
  statementBalance: number;
  printed: boolean;
}

export interface EnquiryRowDto {
  transactionId: string;
  customerCode: string;
  customerName: string;
  description: string;
  targetName: string | null;
  bankName: string | null;
  creditAmount: number;
  debitAmount: number;
  transactionDate: string;
  entryDate: string;
  printed: boolean;
  agentName: string;
  fileName: string | null;
  watchStatus: WatchStatus;
}

export interface EnquiryResultDto {
  rows: EnquiryRowDto[];
  /** True when more rows matched than the server returns in one search. */
  truncated: boolean;
}

export interface ApiErrorBody {
  statusCode: number;
  message: string;
  code?: string;
  details?: Array<{ path: string; message: string }>;
}
