var gulp    = require('gulp'),
    cssmin  = require('gulp-cssmin'),
    concat  = require('gulp-concat'),
    less    = require('gulp-less'),
    rename  = require('gulp-rename'),
    uglify  = require('gulp-uglify'),
    rimraf  = require('rimraf'),
    bower   = require('gulp-bower'),
    mainFiles = require('main-bower-files');

var paths = {
    static: "./erp/static/"
};

paths.js = paths.static + "js/**/*.js";
paths.minJs = paths.static + "js/**/*.min.js";
paths.css = paths.static + "css/**/*.css";
paths.minCss = paths.static + "css/**/*.min.css";
paths.concatJsDest = paths.static + "js/site.min.js";
paths.concatCssDest = paths.static + "css/site.min.css";
paths.fonts = paths.static + "fonts/";
paths.lib = paths.static + "lib/";
paths.bower_components = "./bower_components/";

// deletes the site.min.js file
gulp.task("clean:js", function (cb) {
    rimraf(paths.concatJsDest, cb)
});

// deletes the site.min.css file
gulp.task("clean:css", function (cb) {
    rimraf(paths.concatCssDest, cb);
});

// cleanup both min.js and min.css files
gulp.task("clean", ["clean:js", "clean:css"]);

// gets the contents of .js files from paths.js except the paths.minJs,
// pipe ('|') concat it to paths.concatJsDest, then run uglify
gulp.task("min:js", function () {
    gulp.src([paths.js, "!" + paths.minJs])
        .pipe(concat(paths.concatJsDest))
        .pipe(uglify())
        .pipe(gulp.dest("."));
});

// gets the contents of .css files from paths.css except the paths.minCss,
// pipe ('|') concat it to paths.concatCssDest, then run cssmin
gulp.task("min:css", function () {
    gulp.src([paths.css, "!" + paths.minCss])
        .pipe(concat(paths.concatCssDest))
        .pipe(cssmin())
        .pipe(gulp.dest("."));
});

// perform all min tasks
gulp.task("min", ["min:js", "min:css"]);

// download bower components and copy main files to lib directory
gulp.task("bower:download", function() {
    return bower().pipe(gulp.dest(paths.bower_components));
});

gulp.task("bower", ["bower:download"],  function() {
    // fonts
    gulp.src(mainFiles("**/*(*.eot|*.svg|*.ttf|*.woff|*.woff2)"))
        .pipe(gulp.dest(paths.fonts));

    // less
    gulp.src(mainFiles("**/*.less"))
        .pipe(less())
        .pipe(cssmin())
        .pipe(rename({ extname: ".min.css" }))
        .pipe(gulp.dest(paths.lib));

    // css
    gulp.src(mainFiles(["**/*.css", "!**/*.min.css"]))
        .pipe(cssmin())
        .pipe(rename({ extname: ".min.css" }))
        .pipe(gulp.dest(paths.lib));

    // js
    gulp.src(mainFiles(["**/*.js", "!**/*.min.js"]))
        .pipe(uglify())
        .pipe(rename({ extname: ".min.js" }))
        .pipe(gulp.dest(paths.lib));

    // min.css
    gulp.src(mainFiles("**/*.min.css"))
        .pipe(gulp.dest(paths.lib));

    // min.js
    gulp.src(mainFiles("**/*.min.js"))
        .pipe(gulp.dest(paths.lib));
});

// default task
gulp.task("default", ["bower", "clean", "min"]);