import { createParamDecorator, SetMetadata, type ExecutionContext } from '@nestjs/common';
import type { AccessRight, PermissionCode, SessionUser } from '@transmatch/shared';
import type { Request } from 'express';

export const IS_PUBLIC = 'auth:public';
export const REQUIRED_PERMISSION = 'auth:permission';

export interface PermissionRequirement {
  code: PermissionCode;
  right: AccessRight;
}

/** Marks a route as reachable without a session. */
export const Public = () => SetMetadata(IS_PUBLIC, true);

/** Requires the given right on a permission; on a controller it applies to every route. */
export const RequirePermission = (code: PermissionCode, right: AccessRight = 'VIEW') =>
  SetMetadata(REQUIRED_PERMISSION, { code, right } satisfies PermissionRequirement);

export type AuthenticatedRequest = Request & { user: SessionUser };

/** The signed-in user of the current request. */
export const CurrentUser = createParamDecorator(
  (_data: unknown, ctx: ExecutionContext) => ctx.switchToHttp().getRequest<AuthenticatedRequest>().user,
);
