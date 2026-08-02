import mysql from "mysql2/promise";
import fs from "node:fs/promises";
import path from "node:path";

const OUTPUT_DIRECTORY = path.join(
  process.cwd(),
  "public",
  "images",
  "animals"
);

function slugify(value = "animal") {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
}

function getExtension(contentType = "") {
  const normalizedType = contentType.toLowerCase();

  if (normalizedType.includes("image/png")) {
    return ".png";
  }

  if (normalizedType.includes("image/webp")) {
    return ".webp";
  }

  if (
    normalizedType.includes("image/jpeg") ||
    normalizedType.includes("image/jpg")
  ) {
    return ".jpg";
  }

  if (normalizedType.includes("image/gif")) {
    return ".gif";
  }

  return ".jpg";
}

async function downloadImage(imageUrl) {
  const response = await fetch(imageUrl, {
    redirect: "follow",
    headers: {
      "User-Agent":
        "Mozilla/5.0 PawConnect Image Downloader",
      Accept: "image/avif,image/webp,image/png,image/jpeg,*/*",
    },
  });

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status} ${response.statusText}`
    );
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (!contentType.startsWith("image/")) {
    throw new Error(
      `URL did not return an image. Content-Type: ${contentType}`
    );
  }

  const arrayBuffer = await response.arrayBuffer();

  return {
    buffer: Buffer.from(arrayBuffer),
    extension: getExtension(contentType),
  };
}

async function main() {
  await fs.mkdir(OUTPUT_DIRECTORY, {
    recursive: true,
  });

  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || "localhost",
    port: Number(process.env.DB_PORT || 3306),
    user: process.env.DB_USER || "root",
    password: process.env.DB_PASSWORD || "",
    database: process.env.DB_NAME || "pawconnect",
  });

  try {
    const [animals] = await connection.execute(`
      SELECT id, name, image_url
      FROM animals
      WHERE image_url IS NOT NULL
        AND TRIM(image_url) <> ''
      ORDER BY id ASC
    `);

    console.log(`Found ${animals.length} animal records.\n`);

    let downloaded = 0;
    let skipped = 0;
    let failed = 0;

    for (const animal of animals) {
      const imageUrl = animal.image_url?.trim();

      if (!imageUrl) {
        skipped++;
        continue;
      }

      if (imageUrl.startsWith("/images/animals/")) {
        console.log(
          `Skipped ${animal.id}: already using a local image`
        );
        skipped++;
        continue;
      }

      if (
        !imageUrl.startsWith("http://") &&
        !imageUrl.startsWith("https://")
      ) {
        console.log(
          `Skipped ${animal.id}: unsupported URL ${imageUrl}`
        );
        skipped++;
        continue;
      }

      try {
        console.log(
          `Downloading ${animal.id}: ${animal.name}`
        );

        const { buffer, extension } =
          await downloadImage(imageUrl);

        const safeName =
          slugify(animal.name) || "animal";

        const fileName =
          `${animal.id}-${safeName}${extension}`;

        const localFilePath = path.join(
          OUTPUT_DIRECTORY,
          fileName
        );

        const databasePath =
          `/images/animals/${fileName}`;

        await fs.writeFile(localFilePath, buffer);

        await connection.execute(
          `
            UPDATE animals
            SET image_url = ?
            WHERE id = ?
          `,
          [databasePath, animal.id]
        );

        console.log(`Saved: ${databasePath}\n`);
        downloaded++;
      } catch (error) {
        console.error(
          `Failed ${animal.id} (${animal.name}): ${error.message}\n`
        );
        failed++;
      }

      // Small delay to reduce rate-limit problems.
      await new Promise((resolve) =>
        setTimeout(resolve, 400)
      );
    }

    console.log("Finished.");
    console.log(`Downloaded: ${downloaded}`);
    console.log(`Skipped: ${skipped}`);
    console.log(`Failed: ${failed}`);
  } finally {
    await connection.end();
  }
}

main().catch((error) => {
  console.error("Download process failed:", error);
  process.exit(1);
});