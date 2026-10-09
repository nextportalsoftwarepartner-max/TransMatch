import { Body, Controller, Get, HttpCode, Inject, Post, Req, Res } from '@nestjs/common';
import {
  changePasswordSchema,
  loginSchema,
  type ChangePasswordInput,
  type LoginInput,
  type SessionUser,
} from '@transmatch/shared';
import type { Request, Response } from 'express';
import { ZodPipe } from '../common/zod.pipe.js';
import { APP_CONFIG, type AppConfig } from '../config/app-config.js';
import { CurrentUser, Public } from './auth.decorators.js';
import { SESSION_COOKIE } from './auth.guard.js';
import { AuthService } from './auth.service.js';

@Controller('auth')
export class AuthController {
  constructor(
    private readonly auth: AuthService,
    @Inject(APP_CONFIG) private readonly config: AppConfig,
  ) {}

  @Public()
  @Post('login')
  @HttpCode(200)
  async login(
    @Body(new ZodPipe(loginSchema)) body: LoginInput,
    @Req() req: Request,
    @Res({ passthrough: true }) res: Response,
  ): Promise<SessionUser> {
    const { token, user } = await this.auth.login(body.loginId, body.password, {
      ip: req.ip,
      userAgent: req.get('user-agent'),
    });
    res.cookie(SESSION_COOKIE, token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: this.config.auth.cookieSecure,
      maxAge: this.auth.sessionMaxAgeMs,
      path: '/',
    });
    return user;
  }

  @Public()
  @Post('logout')
  @HttpCode(204)
  logout(@Res({ passthrough: true }) res: Response): void {
    res.clearCookie(SESSION_COOKIE, { path: '/' });
  }

  @Get('me')
  me(@CurrentUser() user: SessionUser): SessionUser {
    return user;
  }

  @Post('change-password')
  @HttpCode(204)
  async changePassword(
    @CurrentUser() user: SessionUser,
    @Body(new ZodPipe(changePasswordSchema)) body: ChangePasswordInput,
  ): Promise<void> {
    await this.auth.changePassword(user.userId, body.currentPassword, body.newPassword);
  }
}
