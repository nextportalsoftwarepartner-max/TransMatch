import {
  ForbiddenException,
  Injectable,
  UnauthorizedException,
  type CanActivate,
  type ExecutionContext,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { can } from '@transmatch/shared';
import type { Request } from 'express';
import { IS_PUBLIC, REQUIRED_PERMISSION, type PermissionRequirement } from './auth.decorators.js';
import { AuthService } from './auth.service.js';

export const SESSION_COOKIE = 'tm_session';

/**
 * Applied to every route: requires a valid session unless the route is
 * @Public(), then enforces @RequirePermission() where one is declared.
 */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly auth: AuthService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const targets = [context.getHandler(), context.getClass()];
    if (this.reflector.getAllAndOverride<boolean>(IS_PUBLIC, targets)) return true;

    const request = context.switchToHttp().getRequest<Request & { user?: unknown }>();
    const token: string | undefined = request.cookies?.[SESSION_COOKIE];
    const user = token ? await this.auth.resolveSession(token) : null;
    if (!user) {
      throw new UnauthorizedException({ statusCode: 401, message: 'Please sign in.', code: 'NOT_AUTHENTICATED' });
    }
    request.user = user;

    const required = this.reflector.getAllAndOverride<PermissionRequirement | undefined>(REQUIRED_PERMISSION, targets);
    if (required && !can(user, required.code, required.right)) {
      throw new ForbiddenException({
        statusCode: 403,
        message: 'You do not have access to this function.',
        code: 'FORBIDDEN',
      });
    }
    return true;
  }
}
