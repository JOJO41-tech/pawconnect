"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();

  const profileRef = useRef(null);

  const [currentUser, setCurrentUser] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);
  const [profileMenuOpen, setProfileMenuOpen] =
    useState(false);

  useEffect(() => {
    loadCurrentUser();
  }, [pathname]);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (
        profileRef.current &&
        !profileRef.current.contains(event.target)
      ) {
        setProfileMenuOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleOutsideClick
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
    };
  }, []);

  function loadCurrentUser() {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      setCurrentUser(null);
      return;
    }

    try {
      setCurrentUser(JSON.parse(savedUser));
    } catch {
      localStorage.removeItem("user");
      setCurrentUser(null);
    }
  }

  function handleLogout() {
    localStorage.removeItem("user");

    setCurrentUser(null);
    setProfileMenuOpen(false);
    setMobileMenuOpen(false);

    router.push("/");
    router.refresh();
  }

  function closeMenus() {
    setMobileMenuOpen(false);
    setProfileMenuOpen(false);
  }

  const profileInitial =
    currentUser?.name?.charAt(0)?.toUpperCase() || "U";

  return (
    <header className="sticky top-0 z-50 border-b border-emerald-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 px-6 py-4">
        <Link
          href="/"
          onClick={closeMenus}
          className="flex items-center gap-3"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100 text-2xl">
            🐾
          </div>

          <div>
            <p className="text-xl font-black text-emerald-900">
              PawConnect
            </p>

            <p className="text-xs font-bold text-slate-500">
              Find. Match. Adopt.
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-2 lg:flex">
          <DesktopNavLink
            href="/"
            label="Home"
            pathname={pathname}
          />

          <DesktopNavLink
            href="/animals"
            label="Browse Pets"
            pathname={pathname}
          />

          <Link
            href="/ai-assistant"
            className={`rounded-full px-5 py-2.5 font-extrabold transition ${
              pathname === "/ai-assistant"
                ? "bg-violet-700 text-white"
                : "bg-violet-100 text-violet-800 hover:bg-violet-200"
            }`}
          >
            ✨ AI Pet Match
          </Link>

          <DesktopNavLink
            href="/#how-it-works"
            label="How It Works"
            pathname={pathname}
          />

          <DesktopNavLink
            href="/shelter-login"
            label="For Shelters"
            pathname={pathname}
          />

          {currentUser ? (
            <div
              ref={profileRef}
              className="relative ml-2"
            >
              <button
                type="button"
                onClick={() =>
                  setProfileMenuOpen(
                    (current) => !current
                  )
                }
                className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 py-1.5 pl-1.5 pr-3 font-bold text-emerald-900 transition hover:bg-emerald-100"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-700 font-black text-white">
                  {profileInitial}
                </span>

                <span className="max-w-28 truncate">
                  {currentUser.name || "Profile"}
                </span>

                <span className="text-xs text-emerald-700">
                  ▾
                </span>
              </button>

              {profileMenuOpen && (
                <div className="absolute right-0 mt-3 w-64 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
                  <div className="border-b border-slate-200 px-5 py-4">
                    <p className="font-black text-slate-900">
                      {currentUser.name || "User"}
                    </p>

                    <p className="mt-1 truncate text-sm text-slate-500">
                      {currentUser.email || ""}
                    </p>
                  </div>

                  <ProfileLink
                    href="/dashboard"
                    onClick={closeMenus}
                  >
                    <span>👤</span>
                    User Dashboard
                  </ProfileLink>

                  <ProfileLink
                    href="/my-applications"
                    onClick={closeMenus}
                  >
                    <span>📋</span>
                    My Applications
                  </ProfileLink>

                  <ProfileLink
                    href="/ai-assistant"
                    onClick={closeMenus}
                  >
                    <span>✨</span>
                    AI Pet Match
                  </ProfileLink>

                  <div className="border-t border-slate-200">
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex w-full items-center gap-3 px-5 py-3 text-left font-bold text-red-600 hover:bg-red-50"
                    >
                      <span>↪</span>
                      Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="ml-2 flex items-center gap-3">
              <Link
                href="/login"
                className="rounded-xl px-4 py-2.5 font-bold text-slate-700 hover:bg-slate-100 hover:text-emerald-700"
              >
                Login
              </Link>

              <Link
                href="/register"
                className="rounded-xl bg-emerald-700 px-5 py-3 font-extrabold text-white transition hover:bg-emerald-800"
              >
                Create Account
              </Link>
            </div>
          )}
        </nav>

        <button
          type="button"
          onClick={() =>
            setMobileMenuOpen((current) => !current)
          }
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-xl hover:bg-slate-50 lg:hidden"
          aria-label="Toggle navigation"
        >
          {mobileMenuOpen ? "✕" : "☰"}
        </button>
      </div>

      {mobileMenuOpen && (
        <div className="border-t border-slate-200 bg-white px-6 py-5 shadow-lg lg:hidden">
          {currentUser && (
            <div className="mb-4 flex items-center gap-3 rounded-2xl bg-emerald-50 p-4">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-700 font-black text-white">
                {profileInitial}
              </span>

              <div className="min-w-0">
                <p className="truncate font-black text-emerald-900">
                  {currentUser.name || "User"}
                </p>

                <p className="truncate text-sm text-slate-500">
                  {currentUser.email || ""}
                </p>
              </div>
            </div>
          )}

          <div className="space-y-2 font-bold">
            <MobileNavLink
              href="/"
              pathname={pathname}
              onClick={closeMenus}
            >
              🏠 Home
            </MobileNavLink>

            <MobileNavLink
              href="/animals"
              pathname={pathname}
              onClick={closeMenus}
            >
              🐾 Browse Pets
            </MobileNavLink>

            <MobileNavLink
              href="/ai-assistant"
              pathname={pathname}
              onClick={closeMenus}
              special
            >
              ✨ AI Pet Match
            </MobileNavLink>

            <MobileNavLink
              href="/#how-it-works"
              pathname={pathname}
              onClick={closeMenus}
            >
              📖 How It Works
            </MobileNavLink>

            <MobileNavLink
              href="/shelter-login"
              pathname={pathname}
              onClick={closeMenus}
            >
              🏡 For Shelters
            </MobileNavLink>

            {currentUser ? (
              <>
                <div className="my-3 border-t border-slate-200" />

                <MobileNavLink
                  href="/dashboard"
                  pathname={pathname}
                  onClick={closeMenus}
                >
                  👤 User Dashboard
                </MobileNavLink>

                <MobileNavLink
                  href="/my-applications"
                  pathname={pathname}
                  onClick={closeMenus}
                >
                  📋 My Applications
                </MobileNavLink>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="block w-full rounded-xl px-4 py-3 text-left text-red-600 hover:bg-red-50"
                >
                  ↪ Logout
                </button>
              </>
            ) : (
              <>
                <div className="my-3 border-t border-slate-200" />

                <MobileNavLink
                  href="/login"
                  pathname={pathname}
                  onClick={closeMenus}
                >
                  Login
                </MobileNavLink>

                <Link
                  href="/register"
                  onClick={closeMenus}
                  className="block rounded-xl bg-emerald-700 px-4 py-3 text-center font-extrabold text-white hover:bg-emerald-800"
                >
                  Create Account
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function DesktopNavLink({
  href,
  label,
  pathname,
}) {
  const basePath = href.split("#")[0];

  const isActive =
    basePath === "/"
      ? pathname === "/"
      : pathname === basePath ||
        pathname.startsWith(`${basePath}/`);

  return (
    <Link
      href={href}
      className={`rounded-xl px-4 py-2.5 font-bold transition ${
        isActive
          ? "bg-emerald-50 text-emerald-800"
          : "text-slate-700 hover:bg-emerald-50 hover:text-emerald-700"
      }`}
    >
      {label}
    </Link>
  );
}

function ProfileLink({
  href,
  onClick,
  children,
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="flex items-center gap-3 px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50 hover:text-emerald-700"
    >
      {children}
    </Link>
  );
}

function MobileNavLink({
  href,
  pathname,
  onClick,
  children,
  special = false,
}) {
  const basePath = href.split("#")[0];

  const isActive =
    basePath === "/"
      ? pathname === "/"
      : pathname === basePath ||
        pathname.startsWith(`${basePath}/`);

  return (
    <Link
      href={href}
      onClick={onClick}
      className={`block rounded-xl px-4 py-3 transition ${
        special
          ? isActive
            ? "bg-violet-700 text-white"
            : "bg-violet-100 text-violet-800 hover:bg-violet-200"
          : isActive
          ? "bg-emerald-100 text-emerald-900"
          : "text-slate-700 hover:bg-emerald-50 hover:text-emerald-800"
      }`}
    >
      {children}
    </Link>
  );
}